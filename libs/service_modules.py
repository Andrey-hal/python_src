import logging
from datetime import datetime

from shared_libs.system_tools import (
    ServiceManagerWindowsAsync,
)

logger = logging.getLogger("service")
logger.propagate = False
try:
    from models.work_db import *
except:
    logger.critical('Не запущена база данных...')


class HealthStatus:
    def __init__(self, parent):
        self.parent = parent
        self.service_name = parent.name
        self.health = 'unknown'
        self.data = ''
        self.last_event_date = 'unknown'
        self.error_count = 0
        self.sim = False

    def set_last_event(self, date):
        self.last_event_date = date.strftime(
            "%Y-%m-%d %H:%M:%S")
        return self.last_event_date

    def make_error(self, error):
        self.error_count += 1
        self.data = error

    def make_update(self):
        return {
            'service_name': self.service_name,
            'health': self.health,
            'error_count': self.error_count,
            'data': 'Приостановлено для симуляции' if self.sim else self.data,
            'last_event_date': self.last_event_date
        }

    def warning(self, reason=None):
        self.health = 'warning'
        if reason is not None:
            self.data = reason

    def stop(self, reason=None):
        self.health = 'stopped'
        if reason is not None:
            self.data = reason

    def pause(self, reason=None):
        self.health = 'paused'
        if reason is not None:
            self.data = reason

    def ok(self, reason=None):
        self.health = 'ok'
        if reason is not None:
            self.data = reason

    def unknown(self, reason=None):
        self.health = 'unknown'
        if reason is not None:
            self.data = reason

    def stopping(self, reason=None):
        self.health = 'stopping'
        if reason is not None:
            self.data = reason

    def starting(self, reason=None):
        self.health = 'stopping'
        if reason is not None:
            self.data = reason

    def down(self, reason=None):
        self.health = 'down'
        self.make_error(reason)
        if reason is not None:
            self.data = reason


class LocalService:
    type = 'local_service'

    def __init__(self, name, service_name, active=False, need_db=False, simulation_stop=False):
        self.name = name
        self.service_name = service_name
        self.active = active
        self.need_db = need_db
        self.simulation_stop = simulation_stop
        self.health = HealthStatus(self)
        self.service = None

    def init(self):
        self.get_status()
        self.active = True

    def get_status(self):
        if self.service is None:
            self.service = ServiceManagerWindowsAsync(self.service_name)
        status = self.service.status()
        if status == 'STOPPED':
            self.health.stop()
        elif status == 'STARTING':
            self.health.starting()
        elif status == 'STOPPING':
            self.health.stopping()
        elif status == 'RUNNING':
            self.health.ok()
        else:
            self.health.unknown()

        return self.health

    async def start(self):
        if self.health.health in ['RUNNING', 'STARTING']:
            return self.health.health
        result = await self.service.start()

        return result

    async def stop(self):
        if self.health.health in ['STOPPING', 'STOPPED']:
            return self.health.health
        result = await self.service.stop()
        return result

    async def restart(self):
        await self.service.restart()


class LocalModule:
    type = 'local_module'

    def __init__(self, name, _module, _import, active=False, need_db=False, simulation_stop=False):
        self.name = name
        self._module = _module
        self.active = False
        self.need_db = need_db
        self.simulation_stop = simulation_stop
        self._import = _import
        self.module = None
        self.log = None

        self.health = HealthStatus(self)

        pass

    def init(self):
        try:
            exec(self._import)
        except Exception as e:
            raise ImportError(e)
        self.module = eval(self._module)()
        self.log = self.module.log
        self.get_status()
        self.active = True

    async def start(self):
        if self.module is None:
            self.init()
        if self.module.stop_flag:
            self.module.stop_flag = False
        if self.module.pause:
            self.module.pause = False

        self.module.start()

    async def pause(self, t=None, sim=False):
        if type(t) is bool:
            self.module.pause = t
            if sim:
                self.health.sim = t
            return

        if self.module.pause:
            self.module.pause = False
            if sim:
                self.health.sim = False
        else:
            if sim:
                self.health.sim = True
            self.module.pause = True

    async def stop(self):
        if self.module is not None:
            self.module.stop_flag = True

    async def restart(self):

        await self.stop()
        await self.start()

    def get_status(self):
        status = None
        if self.module is None:
            if self.health.health != 'down':
                self.health.down('Ошибка импорта')
            return self.health
        if self.need_db:
            try:
                with db_session:
                    db_health = Health[self.name]
                delta = datetime.now() - db_health.tmstp
                normal_delta = 10
                self.health.set_last_event(db_health.tmstp)
                if delta.seconds > normal_delta:
                    status = 'warning'
                    self.health.warning('Сервис не писал своё состояние больше 10 секунд')
                else:

                    self.health.ok('')
            except pony.orm.core.ObjectNotFound:
                status = "warning"
                self.health.warning("Нет записи состояния в базе данных, данные могут быть не актуальны")
                logger.error(
                    "[{}] Ошибка, запись о состоянии не существует в базе данных.".format(self.name)
                )

        if hasattr(self.module, "status") and status != 'warning':
            if self.module.status == 'starting':
                self.health.starting()
            elif self.module.status == 'ok':
                self.health.ok()
            elif self.module.status == 'down':
                self.health.down()
            elif self.module.status == 'stopped':
                if self.module.stop_flag:
                    self.health.stop()
                else:
                    self.health.warning()
            elif self.module.status == 'stopping':
                self.health.stopping()
        elif status != 'warning':
            self.health.unknown('Сервис не предостовляет свой статус')

        elif status == 'warning' and self.module is not None and self.module.stop_flag:
            self.health.stop()

        if hasattr(self.module, "pause"):
            if self.module.pause:
                self.health.pause()

        return self.health
