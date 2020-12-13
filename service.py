import ctypes
import os
from datetime import datetime
from time import sleep
from logs import logging, StreamHandler
from shared_libs.system_tools import (
    is_user_admin,
    ServiceManagerWindows,
)
#
from configs import Conf
from traceback import format_exc

from libs.service_modules import LocalModule, LocalService

from modules.simulator.main import Simulator
from modules.websocket_server.main import *
from modules.websocket_server.scheme import Action
from modules.websocket_server.scheme import Update
from shared_libs.read_log import read_log


logger = logging.getLogger("service")
logger.propagate = False


def start_minimal():
    try:
        db = ServiceManagerWindows("PostgreSQL")
        logger.debug('Db service status: {}'.format(db.status()))
        if db.status() not in ["RUNNING", "STARTING"]:
            db.start()
        sleep(5)
    except:
        logger.critical('Запуск невозможен. База данных не найдена или не может быть запущена.')
        logger.critical(format_exc())
        raise SystemExit


start_minimal()
# Проверка системы на возможность управления сервисами
if os.name == "nt":
    service_features = True
    MessageBox = ctypes.windll.user32.MessageBoxW

config = Conf("config.ini")

# Запуск нужных сервисов


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

Services = {
    # 'opc_reader': LocalModule(name='opc_reader',
    #                           _module='ReaderMain',
    #                           _import='from modules.OPC_reader.main import ReaderMain',
    #                           active=False,
    #                           need_db=True,
    #                           simulation_stop=True),
    'modbus_reader': LocalModule(name='modbus_reader',
                                 _module='ModbusReaderMain',
                                 _import='from modules.modbus_reader.main import ModbusReaderMain',
                                 active=False,
                                 need_db=True,
                                 simulation_stop=True),
    'python_calc': LocalModule(name='python_calc',
                               _module='CalculationMain',
                               _import='from modules.calculation_module.main import CalculationMain',
                               active=False,
                               need_db=True,
                               simulation_stop=True),
    'db': LocalService(name='db',
                       service_name='PostgreSQL',
                       active=False,
                       need_db=False,
                       simulation_stop=False)
}

try:
    Simulator_inited = Simulator(db=work_db.work_db, db_session=db_session)
except:
    logger.error("Ошибка иницизиализаци сервиса")


# noinspection PyUnresolvedReferences,PyBroadException,PyTypeChecker
class Service:
    def __init__(self):
        self.loop = asyncio.get_event_loop()  # сердце
        self.tasks = {}
        self.min_log_lvl = config.config['logging']['service_lvl']
        self.log_lvl = ["INFO", "WARNING", "ERROR", "DEBUG", "CRITICAL"]

    # Цикл обновления состояния
    @staticmethod
    async def get_status():
        global use_work_db
        while True:
            try:
                statuses = []
                for name, service in Services.items():
                    statuses.append(service.get_status().make_update())
                await Service.new_update(statuses, "status")
                await asyncio.sleep(0.3)
            except:
                pass

    # Внедрение логгинга в подчинённых
    async def inject_logging(self):
        for name, service in Services.items():
            if service.type == 'local_module' and service.active:
                hndl = InjectedHandler()
                hndl.setLevel(logging.getLevelName(self.min_log_lvl))
                service.log.propagate = False
                service.log.addHandler(hndl)

    async def control_service(self, name, action):
        try:
            service = Services[name]
            if action == 'stop':
                await service.stop()
            elif action == 'play':
                await service.start()
            elif action == 'pause':
                await service.pause()
            elif action == 'sim_pause':
                await service.pause(True, sim=True)
            elif action == 'sim_unpause':
                await service.pause(False, sim=True)
            elif action == "restart":
                await service.restart()
            else:
                logger.error('Неизвестная команда {} для сервиса {}'.format(action, name))
        except:
            logger.error('Ошибка выполнения комманды {} для сервиса {}'.format(action, name))
            logger.error(format_exc())

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
                event = await internal_conveyor.get()

                if event["type"] is "log":
                    if event["log"]["lvl"] not in self.log_lvl:
                        continue
                    await self.new_update([event["log"]], "log")

                elif event["type"] is "service_control":

                    await self.control_service(
                        name=event["service_control"].service_name,
                        action=event["service_control"].control_type,
                    )
            except:
                pass

    """
    Хэндлеры(обработчики) для вэбсокета
    """

    @staticmethod
    @handler(action=Action.ServiceControl)
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
    @handler(action=Action.InitSimulator)
    async def init_simulator(data, client):
        try:
            data = {
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
            await Service.new_update(data, "simulator")
        except:
            log.error('Ошибка инициализации симулятора')
            log.error(format_exc())
            pass

    @staticmethod
    @handler(action="simulator_control")
    async def simulator(data, client):
        if "position" in data.simulator_control:
            Simulator_inited.seek(int(data.simulator_control["position"]))
        if "play" in data.simulator_control:
            Simulator_inited.play = data.simulator_control['play']
        if "active" in data.simulator_control:
            Simulator_inited.active = data.simulator_control['active']
            for name, service in Services.items():
                if service.simulation_stop:

                    if data.simulator_control["active"]:
                        action_type = "sim_pause"
                        Simulator_inited.write_to_base()
                    else:
                        action_type = "sim_unpause"

                    internal_conveyor.put_nowait({
                        "type": "service_control",
                        "service_control": {
                            "action_type": action_type,
                            "service_name": name,
                        },
                    })
        data = {
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
        await Service.new_update(data, "simulator")

    @staticmethod
    @notify(['all'])
    def new_update(data, update_type):
        updates = Update.Updates()
        delta = datetime.now() - start_time
        updates += Update.Uptime(time=str(delta).split(".")[0])

        if update_type == "status":
            for s in data:
                t = Update.Health(**s)
                try:
                    updates += t
                except:
                    print(format_exc())
        elif update_type == "log":
            t = Update.Log(logs=data)
            updates += t

        elif update_type == "simulator":
            t = Update.Simulator(**data)
            updates += t

        return updates

    async def prepare_services(self):
        for name, service in Services.items():
            try:
                service.init()
                await service.start()
            except ImportError:
                logger.error('Ошибка импорта {}'.format(name))
            except SystemExit as e:
                logger.error("Ошибка запуска модуля {}, {}.".format(
                    name, e))
                logger.error(format_exc())
            except NameError as e:
                logger.error("Ошибка запуска сервиса {}. Не найдено. {}.".format(
                    name, e))
            except PermissionError as e:
                logger.error("Ошибка запуска сервиса {}. Нет доступа. {}.".format(
                    name, e))
            except TimeoutError as e:
                logger.error("Ошибка запуска сервиса {}. Таймаут запуска. {}.".format(
                    name, e))
            except:
                logger.error("Ошибка запуска сервиса {}. Неизвестная ошибка ".format(
                    name))
                logger.error(format_exc())

    def start(self):
        # tasks = [ioloop.create_task(foo()), ioloop.create_task(bar())]
        # wait_tasks = asyncio.wait(tasks)
        # ioloop.run_until_complete(wait_tasks)
        # self.loop.run_until_complete(self.open_server(ip, int(port)))
        self.loop.run_until_complete(start_server)
        self.loop.create_task(self.prepare_services())
        self.loop.create_task(self.inject_logging())
        self.loop.create_task(self.events_worker())
        self.loop.create_task(self.get_status())
        from modules.plugin_manager import main
        # self.loop.run_until_complete(start_server)

        self.loop.run_forever()


Service().start()
