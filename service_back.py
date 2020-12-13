import os
import ctypes
from datetime import datetime

from logs import logging, StreamHandler

from shared_libs.system_tools import (
    is_user_admin,
    ServiceManagerWindowsAsync,
    ServiceManagerWindows,
)
from shared_libs.read_log import read_log
from modules.websocket_server.main import *
from modules.simulator.main import Simulator
from configs import Conf

logger = logging.getLogger("service")
logger.propagate = False

# Проверка системы на возможность управления сервисами
if os.name == "nt":
    service_features = True
    MessageBox = ctypes.windll.user32.MessageBoxW

config = Conf("config.ini")

# Запуск нужных сервисов
def start_minimal():
    try:
        db = ServiceManagerWindows("PostgreSQL")
        logger.debug('Db service status: {}'.format(db.status()))
        if db.status() not in ["RUNNING", "STARTING"]:
            db.restart()
    except:
        logger.critical('Запуск невозможен. База данных не найдена или не может быть запущена.')
        logger.critical(format_exc())

start_minimal()

# Проверка на права администратора
try:
    if is_user_admin():
        pass
    else:
        logger.warning("Управление сервисами недоступно. Запустите от имени администратора.")
        raise SystemExit
except:
    logger.critical("Управление сервисами недоступно. Запустите от имени администратора.")
    raise SystemExit

# Проверка подключения к базе данных
try:
    use_work_db = True
    from models.work_db import *
    from models.local_db import *
except:
    use_work_db = False
    logger.error("Невозможно подключиться к основной базе")

########################################################################################################################

start_time = datetime.now()  # Для аптайма

internal_conveyor = asyncio.Queue()

# Хэндлер для логгеров подчинённых
class InjectedHandler(StreamHandler):
    def emit(self, record):
        self.format(record)
        a = {
            "module": record.name,
            "date": datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"),
            "lvl": record.levelname,
            "data": record.message,
        }
        internal_conveyor.put_nowait({"type": "log", "log": a})
        return True


hndl = InjectedHandler()
hndl.setLevel(logging.DEBUG)
logger.addHandler(hndl)

Services = [
    {
        "active": False,
        "service_name": "opc_reader",
        "display_name": "OPC reader",
        "need_db": True,
        "simulation_stop": True,
        "type": "local_module",
        "module": "ReaderMain",
        "import": "from modules.OPC_reader.main import ReaderMain",
    },
    {
        "active": False,
        "service_name": "python_calc",
        "display_name": "Calculation Module",
        "need_db": True,
        "type": "local_module",
        "module": "CalculationMain",
        "import":
            "from modules.calculation_module.main import CalculationMain",
    },
    {
        "active": False,
        "service_name": "db",
        "display_name": "Database",
        "need_db": False,
        "type": "local_service",
        "sys_service_name": "PostgreSQL",
        "sys_service": None,
    },
]

try:
    Simulator_inited = Simulator(db=work_db.work_db, db_session=db_session)
except:
    logger.error("Ошибка иницизиализаци сервиса")


# noinspection PyUnresolvedReferences,PyBroadException,PyTypeChecker
class Service:
    def __init__(self):
        self.loop = asyncio.get_event_loop()  # сердце

        for n, s in enumerate(Services):
            Services[n]["status"] = {
                "service_name": s["service_name"],
                "health": "unknown",
                "data": "",
                "last_log": "",
                "last_event_date": "unknown",
                "last_health": "unknown",
                "error_count": 0,
                "stop_flag": False,
            }

        self.tasks = {}
        self.min_log_lvl = config.config['logging']['service_lvl']
        self.log_lvl = ["INFO", "WARNING", "ERROR", "DEBUG", "CRITICAL"]

    # Цикл обновления состояния
    async def get_status(self):
        global use_work_db
        while True:
            for n, s in enumerate(Services):
                service = Services[n]
                service: Services[0]
                name = service["service_name"]

                if not service["active"]:
                    service["status"]["health"] = 'down'
                if service["type"] is "local_service" and service["active"]:
                    if "sys_service" in service:
                        service_status = service["sys_service"].status()
                        if service_status == "RUNNING":
                            health = "ok"
                        elif service_status == "STOPPED":
                            if service["status"]["stop_flag"]:
                                health = "stopped"
                            else:
                                health = "down"
                        elif service_status == "STOPPING":
                            health = "stopping"
                        elif service_status == "STARTING":
                            health = "starting"
                        else:
                            health = "unknown"
                        if "db" in name:
                            if health is "ok":
                                use_work_db = True
                            else:
                                use_work_db = False

                        service["status"]["health"] = health
                        if service["status"]["health"] is "ok":
                            service["status"][
                                "last_event_date"] = datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S")

                elif service["type"] is "local_module" and service["active"]:
                    service["status"]["health"] = self.check_module_status(
                        service)

                if service["need_db"] and use_work_db:
                    with db_session:
                        try:
                            db_health = Health[name]

                        except pony.orm.core.ObjectNotFound:
                            service["status"]["health"] = "warning"
                            service["status"][
                                "data"] = "Нет записи состояния в базе данных, данные могут быть не актуальны"
                            logger.error(
                                "Ошибка,  запись о состоянии не существует в базе данных."
                            )
                            continue

                        except:
                            use_work_db = False
                            logger.error("Отвал базы")
                            continue

                        delta = datetime.now() - db_health.tmstp
                        normal_delta = (
                            db_health.params["period"]
                            if "period" in db_health.params else
                            10  # Жестко заданный параметр
                        )

                        if delta.seconds > normal_delta and service["status"][
                            "health"] not in [
                            "stopped", "down", "warning", "paused"
                        ]:
                            service["status"].update(
                                health="warning",
                                last_event_date=db_health.tmstp.strftime(
                                    "%Y-%m-%d %H:%M:%S"),
                                data="Сервис не писал своё состояние больше 10 секунд",
                            )

                        elif delta.seconds <= normal_delta and service[
                            "status"]["health"] not in [
                            "stopped", "down", "warning", "paused"
                        ]:
                            service["status"].update(
                                health="ok",
                                last_event_date=db_health.tmstp.strftime(
                                    "%Y-%m-%d %H:%M:%S"),
                                data="",
                            )

                if (service["status"]["health"] !=
                        service["status"]["last_health"]
                        and service["status"]["health"] in ["down"]
                        and service["status"]["last_health"] in [
                            "ok", "started", "unknown"
                        ]):
                    service["status"]["error_count"] += 1

                service["status"]["last_health"] = service["status"]["health"]

            await Service.new_update([i["status"] for i in Services], "status")
            await asyncio.sleep(0.5)

    @staticmethod
    def check_module_status(service):
        """

        :param service:
        :return:
        """
        if hasattr(service["module"], "pause"):
            pause = service["module"].pause
        else:
            pause = False
        if hasattr(service["module"], "status"):
            status = service["module"].status
        else:
            status = "unknown"
        if pause:
            return "paused"
        else:
            return status

    # Внедрение логгинга в подчинённых
    async def inject_logging(self):
        for s in Services:
            if "module" in s and s['active']:
                hndl = InjectedHandler()
                s["log_handler"] = hndl
                hndl.setLevel(logging.getLevelName(self.min_log_lvl))
                s["module"].log.propagate = False
                s["module"].log.addHandler(hndl)

    async def control_service(self, name, action):
        try:
            service = [i for i in Services if i["service_name"] == name][0]
        except IndexError:
            return
        if service["type"] == "local_module":

            if action == "stop":
                if not service["module"].stop_flag:
                    service["module"].stop_flag = True
                    service["module"].status = "stopping"

            elif action == "pause":
                if service["module"].pause:
                    service["module"].pause = False
                else:
                    service["module"].pause = True

            elif action == "play":
                if not service['active']:
                    await self.prepare_service(service=service)

                if service["module"].pause:
                    service["module"].pause = False
                    return

                if service["module"].stop_flag:
                    service["module"].stop_flag = False

                if service["module"].status == "ok":
                    return
                service["module"].start()

            elif action == "sim_pause":
                service["module"].pause = True
                service["status"]["data"] = "Приостановленно для симуляции"

            elif action == "sim_unpause":
                service["module"].pause = False
                service["status"]["data"] = ""

        elif service["type"] == "local_service":
            if action == "stop":
                service["status"]["stop_flag"] = True
                await service["sys_service"].stop()

            elif action == "play":
                service["status"]["stop_flag"] = False
                await service["sys_service"].start()

            elif action == "restart":
                await service["sys_service"].restart()

    async def events_worker(self):
        """
        Цилк обработки внутренних событий
        Пример события в конвейере:
         { "type": "service_control",
            "service_control": {
                    "action_type": action_type,
                    "service_name": i["service_name"],
                },
         }
        :return:
        """
        while True:
            try:
                log_item = await internal_conveyor.get()

                if log_item["type"] is "log":
                    if log_item["log"]["lvl"] not in self.log_lvl:
                        continue
                    await self.new_update([log_item["log"]], "log")

                elif log_item["type"] is "service_control":
                    await self.control_service(
                        name=log_item["service_control"]["service_name"],
                        action=log_item["service_control"]["action_type"],
                    )
            except:
                pass

    """
    Хэндлеры(обработчики) для вэбсокета
    """
    @staticmethod
    @handler(action="service_control")
    async def interface_action(data, client):
        internal_conveyor.put_nowait({
            "type": "service_control",
            "service_control": data
        })

    @staticmethod
    @handler(action="need_log")
    async def request_last_log(data, client):
        log_ = []
        for s in Services:
            if "module" in s and s["active"]:
                log_paths = [
                    handler.baseFilename
                    for handler in s["module"].log.handlers
                    if isinstance(handler, logging.FileHandler)
                ]
                if len(log_paths):

                    log_.extend(read_log(log_paths[0]))
        log_.extend(read_log([handler.baseFilename for handler in logger.handlers if
                     isinstance(handler, logging.FileHandler)][0]))
        log_.sort(
            key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d %H:%M:%S,%f"),
            reverse=True,
        )
        log_ = log_[:300][::-1]
        await Service.new_update(log_, "log")
        return log_

    @staticmethod
    @handler(action="init_simulator")
    async def init_simulator(data, client):
        try:
            d = {
                "type":
                    "updates",
                "updates": [{
                    "update_type":
                        "simulator",
                    "min":
                        Simulator_inited.min,
                    "max":
                        Simulator_inited.max,
                    "position":
                        Simulator_inited.position,
                    "active":
                        Simulator_inited.active,
                    "play":
                        Simulator_inited.play,
                    "variables": [
                        "{} - {}".format(k, v)
                        for k, v in Simulator_inited.variables.items()
                    ]}]
            }
            await client.ws.send(json.dumps(d))
        except:
            pass

    @staticmethod
    @handler(action="simulator_control")
    async def simulator(data, client):
        if "position" in data:
            Simulator_inited.seek(int(data["position"]))
        if "play" in data:
            Simulator_inited.play = data['play']
        if "active" in data:
            Simulator_inited.active = data['active']
            for i in Services:
                if "simulation_stop" in i and i["simulation_stop"]:

                    if data["active"]:
                        action_type = "sim_pause"
                        Simulator_inited.write_to_base()
                    else:
                        action_type = "sim_unpause"

                    internal_conveyor.put_nowait({
                        "type": "service_control",
                        "service_control": {
                            "action_type": action_type,
                            "service_name": i["service_name"],
                        },
                    })
        data = {
            "update_type":
                "simulator",
            "min":
                Simulator_inited.min,
            "max":
                Simulator_inited.max,
            "position":
                Simulator_inited.position,
            "active":
                Simulator_inited.active,
            "play":
                Simulator_inited.play,
            "variables": [
                "{} - {}".format(k, v)
                for k, v in Simulator_inited.variables.items()
            ],
        }
        await Service.new_update(data, "simulation")

    @staticmethod
    @notify
    def new_update(data, update_type):
        delta = datetime.now() - start_time
        done = [{"update_type": "uptime", "time": str(delta).split(".")[0]}]

        if update_type == "status":
            for s in data:
                t = {"update_type": "health"}
                t.update(s)
                done.append(t)
            return done

        elif update_type == "log":
            tr = list([{
                "date": log_item["date"],
                "program": log_item["module"],
                "status": log_item["lvl"],
                "description": log_item["data"],
            } for log_item in data])
            ts = {"update_type": "log", "log": tr}
            done.append(ts)
            return done

        elif update_type == "simulation":
            done.append(data)
            return done

    async def prepare_services(self):
        for n, s in enumerate(Services):
           await  self.prepare_service(n,s)

    async def prepare_service(self,n=None,s=None,service=None):
        if service==None:
            service = Services[n]
        else:
            s= service

        # Локальные питоновксие модули
        if s["type"] is "local_module":
            try:
                try:
                    # Импорт модуля
                    exec(s["import"])
                except:
                    logger.error(format_exc())
                    logger.error("Ошибка импорта {}".format(
                        s["service_name"]))
                    return

                # Инициализация модуля
                module = eval(s["module"])(loop=self.loop)
                service["module"] = module
                service["active"] = True
                self.tasks[s["service_name"]] = module.start()
            except SystemExit as e:
                logger.error("Ошибка запуска модуля {}, {}.".format(
                    s["service_name"], e))

        # Локальные сервисы
        elif s["type"] is "local_service":
            try:
                local_service = ServiceManagerWindowsAsync(
                    s["sys_service_name"])
                if local_service.status() == "STOPPED":
                    logger.info(
                        "Сервис {} не запущен, попытка запуска...".format(
                            s["service_name"]))
                    await local_service.restart()
                service["active"] = True
                service["sys_service"] = local_service
            except NameError as e:
                logger.error("Ошибка запуска сервиса {}, {}.".format(
                    s["service_name"], e))
            except PermissionError as e:
                logger.error("Ошибка запуска сервиса {}, {}.".format(
                    s["service_name"], e))
            except TimeoutError as e:
                logger.error("Ошибка запуска сервиса {}, {}.".format(
                    s["service_name"], e))
            except:
                logger.debug(format_exc())
                logger.error(
                    "Ошибка запуска сервиса {}, Неизвестная ошибка..".
                        format(s["service_name"]))

    def start(self):
        self.loop.run_until_complete(start_server)
        self.loop.create_task(self.prepare_services())
        self.loop.create_task(self.inject_logging())
        self.loop.create_task(self.events_worker())
        self.loop.create_task(self.get_status())

        # self.loop.run_until_complete(start_server)

        self.loop.run_forever()


Service().start()
