import win32service
import win32con
from asyncio import sleep as async_sleep, get_event_loop
from datetime import datetime
import os
import ctypes
import time


def is_user_admin():
    # type: () -> bool
    """Return True if user has admin privileges.

    Raises:
        AdminStateUnknownError if user privileges cannot be determined.
    """
    try:
        return os.getuid() == 0
    except AttributeError:
        pass
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except AttributeError:
        raise PermissionError("Пользователь не имеет прав админисратора!")


class ServiceManagerWindowsAsync(object):
    def __init__(self, name):
        if not is_user_admin():
            raise PermissionError("Пользователь не имеет прав админисратора!")
        self.name = name
        self.desc = None
        self.wait_time = 2
        self.delay_time = 10

        self.scm = win32service.OpenSCManager(
            None, None, win32service.SC_MANAGER_ALL_ACCESS
        )
        self.get_by_name(name)
        if self.is_exists():
            try:
                self.handle = win32service.OpenService(
                    self.scm, self.name, win32service.SC_MANAGER_ALL_ACCESS
                )
            except Exception as e:
                raise NameError("Сервис не найден")
        else:
            raise NameError("Сервис не найден")

    def get_by_name(self, name):
        statuses = win32service.EnumServicesStatus(
            self.scm, win32service.SERVICE_WIN32, win32service.SERVICE_STATE_ALL
        )
        for (short_name, desc, status) in statuses:
            if name.lower() in short_name.lower():
                self.name = short_name
                self.desc = desc
                return

    def is_stop(self):
        flag = False

        if self.handle:
            ret = win32service.QueryServiceStatus(self.handle)
            flag = ret[1] != win32service.SERVICE_RUNNING

        return flag

    async def start(self):
        status_info = win32service.QueryServiceStatus(self.handle)

        if status_info[1] == win32service.SERVICE_RUNNING:
            return True
        try:
            if self.handle:
                win32service.StartService(self.handle, None)
        except Exception as e:
            raise PermissionError("Ошибка запуска сервиса")
        status_info = win32service.QueryServiceStatus(self.handle)

        if status_info[1] == win32service.SERVICE_RUNNING:
            return True
        elif status_info[1] == win32service.SERVICE_START_PENDING:
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).seconds > self.delay_time:
                    raise TimeoutError("Таймаут запуска сервиса")

                time.sleep(self.wait_time)
                if (
                    win32service.QueryServiceStatus(self.handle)[1]
                    == win32service.SERVICE_RUNNING
                ):
                    return True
        else:
            raise PermissionError("Ошибка запуска сервиса")

    async def stop(self):
        try:
            status_info = win32service.ControlService(
                self.handle, win32service.SERVICE_CONTROL_STOP
            )
        except Exception as e:
            raise PermissionError("Ошибка остановки сервиса")
        if status_info[1] == win32service.SERVICE_STOPPED:
            return True
        elif status_info[1] == win32service.SERVICE_STOP_PENDING:
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).seconds > self.delay_time:
                    raise TimeoutError("Таймаут остановки сервиса")

                time.sleep(2)
                if (
                    win32service.QueryServiceStatus(self.handle)[1]
                    == win32service.SERVICE_STOPPED
                ):
                    return True
        else:
            raise PermissionError("Ошибка остановки сервиса")

    async def restart(self):
        if not self.is_stop():
            await self.stop()

        await self.start()
        return self.status()

    def status(self):
        status_info = win32service.QueryServiceStatus(self.handle)
        status = status_info[1]
        if status == win32service.SERVICE_STOPPED:
            return "STOPPED"
        elif status == win32service.SERVICE_START_PENDING:
            return "STARTING"
        elif status == win32service.SERVICE_STOP_PENDING:
            return "STOPPING"
        elif status == win32service.SERVICE_RUNNING:
            return "RUNNING"

    def close(self):
        if self.scm:
            win32service.CloseServiceHandle(self.handle)
            win32service.CloseServiceHandle(self.scm)

    def is_exists(self):
        statuses = win32service.EnumServicesStatus(
            self.scm, win32service.SERVICE_WIN32, win32service.SERVICE_STATE_ALL
        )
        for (short_name, desc, status) in statuses:
            if short_name == self.name:
                return True
        return False


class ServiceManagerWindows(object):
    def __init__(self, name):
        if not is_user_admin():
            raise PermissionError("Пользователь не имеет прав админисратора!")
        self.name = name
        self.desc = None
        self.wait_time = 0.5
        self.delay_time = 10

        self.scm = win32service.OpenSCManager(
            None, None, win32service.SC_MANAGER_ALL_ACCESS
        )
        self.get_by_name(name)
        if self.is_exists():
            try:
                self.handle = win32service.OpenService(
                    self.scm, self.name, win32service.SC_MANAGER_ALL_ACCESS
                )
            except Exception as e:
                raise NameError("Сервис не найден")
        else:
            raise NameError("Сервис не найден")

    def get_by_name(self, name):
        statuses = win32service.EnumServicesStatus(
            self.scm, win32service.SERVICE_WIN32, win32service.SERVICE_STATE_ALL
        )
        for (short_name, desc, status) in statuses:
            if name.lower() in short_name.lower():
                self.name = short_name
                self.desc = desc
                return

    def is_stop(self):
        flag = False

        if self.handle:
            ret = win32service.QueryServiceStatus(self.handle)
            flag = ret[1] != win32service.SERVICE_RUNNING

        return flag

    def start(self):
        try:
            if self.handle:
                win32service.StartService(self.handle, None)
        except Exception as e:
            raise PermissionError("Ошибка запуска сервиса")
        status_info = win32service.QueryServiceStatus(self.handle)

        if status_info[1] == win32service.SERVICE_RUNNING:
            return True
        elif status_info[1] == win32service.SERVICE_START_PENDING:
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).seconds > self.delay_time:
                    raise TimeoutError("Таймаут запуска сервиса")

                time.sleep(self.wait_time)
                if (
                    win32service.QueryServiceStatus(self.handle)[1]
                    == win32service.SERVICE_RUNNING
                ):
                    return True
        else:
            raise PermissionError("Ошибка запуска сервиса")

    def stop(self):
        try:
            status_info = win32service.ControlService(
                self.handle, win32service.SERVICE_CONTROL_STOP
            )
        except Exception as e:
            raise PermissionError("Ошибка остановки сервиса")
        if status_info[1] == win32service.SERVICE_STOPPED:
            return True
        elif status_info[1] == win32service.SERVICE_STOP_PENDING:
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).seconds > self.delay_time:
                    raise TimeoutError("Таймаут остановки сервиса")

                time.sleep(self.wait_time)
                if (
                    win32service.QueryServiceStatus(self.handle)[1]
                    == win32service.SERVICE_STOPPED
                ):
                    return True
        else:
            raise PermissionError("Ошибка остановки сервиса")

    def restart(self):
        if not self.is_stop():
            self.stop()
        self.start()
        return self.status()

    def status(self):
        status_info = win32service.QueryServiceStatus(self.handle)
        status = status_info[1]
        if status == win32service.SERVICE_STOPPED:
            return "STOPPED"
        elif status == win32service.SERVICE_START_PENDING:
            return "STARTING"
        elif status == win32service.SERVICE_STOP_PENDING:
            return "STOPPING"
        elif status == win32service.SERVICE_RUNNING:
            return "RUNNING"

    def close(self):
        if self.scm:
            win32service.CloseServiceHandle(self.handle)
            win32service.CloseServiceHandle(self.scm)

    def is_exists(self):
        statuses = win32service.EnumServicesStatus(
            self.scm, win32service.SERVICE_WIN32, win32service.SERVICE_STATE_ALL
        )
        for (short_name, desc, status) in statuses:
            if short_name == self.name:
                return True
        return False


if __name__ == "__main__":
    loop = get_event_loop()
    app = ServiceManagerWindowsAsync("postgre")

    msg = loop.run_until_complete(app.restart())
    print(msg)
