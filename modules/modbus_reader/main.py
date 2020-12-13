#!/usr/bin/env python
"""
Модуль чтения переменных Modbus TCP сервера Для чтения из клиента.
"""
__log__ = "logs/modbus_reader.log"
__config__ = "configs/modbus_reader.ini"

import asyncio
import traceback
from time import sleep
from modules.modbus_reader.modbus_read import InputModbusDataBlock, run_custom_db_server
from logs import logging
from models.work_db import *

config = Conf("modbus_reader.ini").config

log = logging.getLogger("modbus_reader")
log.propagate = False
source_name = "modbus_reader"


class ModbusReaderMain:
    """
    Класс ридера openOPC сервиса
    """

    def __init__(self, ip=None, port=None, loop=None):
        if ip is None:
            ip = self.server_name = config["connection"]["ip"]
        if port is None:
            port = self.server_name = config["connection"]["port"]
        if loop is None:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.pause = False
        self.stop_flag = False
        self.status = "running"
        self.log = log
        log_paths = [handler.baseFilename for handler in log.handlers if
                     isinstance(handler, logging.FileHandler)]
        self.ip = ip
        self.port = int(port)
        try:
            # self.opc = self.open_client(ip, port)
            # self.client = self.opc
            self.loop.create_task(self.open_server(ip, int(port)))
            self.modbus = InputModbusDataBlock
            self.server = self.modbus
        except Exception as e:
            self.status = 'down'
            log.critical("Ошибка запуска сервера Modbus.")
            log.debug(traceback.format_exc())
            raise SystemExit("Ошибка запуска сервера Modbus-{}.".format(e))

        self.server_name = config["connection"]["server_name"]

        self.read_structure = {
            k.split("/")[-1]: v for k, v in config["variables"].items() if v != "None"
        }
        if not len(self.read_structure):
            log.critical(
                "Ошибка подключения к ModbusTCP. Не установлены переменные."
            )
            raise SystemExit("Ошибка подключения к ModbusTCP. Не установлены переменные.")
        self.check_db()

    @db_session
    def check_db(self):
        live = {
            i.name: i
            for i in select(
                v for v in VariableWork if v.name in list(self.read_structure.values())
            )
        }
        succ = True
        if len(self.read_structure) != len(live):
            self.status = 'down'
            log.critical("Ошибка! В базе отстуствуют нужные переменные!")
            raise SystemExit("Ошибка! В базе отстуствуют нужные переменные!")
        for var_name, var in live.items():
            if var.source in [None, ""]:
                log.info(
                    "Переменная {} не имеет признак источника, присваиваю себе.".format(
                        var_name
                    )
                )
            elif var.source != source_name:
                log.info(
                    "Несоответствие переменных: {} уже присвоена другому источнику({}), присваиваю "
                    "её на {}".format(var_name, var.source, source_name)
                )
            var.source = source_name
        try:
            Health[source_name]
        except pony.orm.core.ObjectNotFound:
            log.info('Отсутвует переменная состояния. Создание...')
            Health(name=source_name, type='service')

        if not succ:
            self.status = 'down'
            log.critical("Ошибка инициализации, выход...")
            raise SystemExit("Ошибка инициализации, выход...")

    @staticmethod
    async def open_server(ip, port):
        await run_custom_db_server(ip, port)

    def connect_to_server(self, server_name=None):
        """
        Подключение к OPC серверу через openOPC Gateway.
        :param server_name: Имя OPC сервера.
        """
        if not server_name:
            server_name = self.server_name
        try:
            # self.opc = self.open_client(self.ip, self.port)
            # self.client = self.opc
            self.modbus = self.open_server(self.ip, int(self.port))
            self.server = self.modbus
            self.opc.connect(server_name)
            self.client.connect(server_name)
            if self.client.info():
                log.info("Успешное подключение к OPC серверу")
                self.status = 'connected'
        except:
            self.status = 'down'
            log.critical("Ошибка подключения к OPC серверу")
            log.debug(traceback.format_exc())

        self.server_name = server_name

    def check_db_alive(self):
        while True:
            try:
                with db_session:
                    Health[source_name]
                    return True
            except:
                pass
            sleep(1)

    async def read(self):
        """
        Цикл чтения из openOPC Gateway
        """
        read_rate = int(config["connection"]["read_rate"])
        while True:
            if self.pause:
                self.status = 'paused'
                await asyncio.sleep(1)
                continue
            if self.stop_flag:
                if self.status == 'down':
                    log.error('Упала база, ожидание подключения...')
                    result = await self.loop.run_in_executor(None, self.check_db_alive)
                    if result:
                        log.info('Подключение возобновлено, продолжение работы.')
                        self.stop_flag = False
                        continue
                    else:
                        await asyncio.sleep(1)
                        continue
                self.status = 'stopped'
                break
            try:
                # address, value = InputModbusDataBlock.get_Values_for_Sphere(InputModbusDataBlock)
                # print('{} {}'.format(value, address))
                # Основная работа
                frame = self.server.read(tuple(self.read_structure.keys()))
                self.loop.run_in_executor(None, self.write_to_base, frame)
                self.status = 'ok'
                await asyncio.sleep(read_rate)

            except Exception as exp:
                if "Pyro4.errors.CommunicationError" in str(exp) or 'rejected' in str(exp):
                    log.error(
                        "Ошибка подключения к openOPC Gateway, переподключение..."
                    )
                    self.status = 'warning'
                    await asyncio.sleep(5)
                    self.connect_to_server()
                    continue
                elif "argument of type 'bool'" in str(exp):
                    log.critical("Переменные для чтения заданы неверно! Выход...")
                    self.status = 'down'
                    self.stop_flag = True
                else:
                    log.error(
                        "Ошибка чтения данных из openOPC Gateway. Проверьте состояние сервиса zzzOpenOPCService"
                    )
                    self.status = 'down'
                    self.stop_flag = True
                    log.debug(traceback.format_exc())

                await asyncio.sleep(2)

            # print("     ".join(["{} - {}".format(i[0], i[1]) for i in readed]))

    @db_session
    def write_to_base(self, frame):
        """
        Запись считанных из openOPC Gateway данных
        :param frame: "Кадр" в формате (Имя из OPC, значение, ...)
        :return:
        """
        # prep_frame = {self.read_structure[i[0]]: i[1] for i in frame}
        try:
            work_db.execute(
                """
                update variablework as v set flo = c.flo,tmstp = c.tmstp
                from (values {} ) as c(name, flo,tmstp) 
                where c.name = v.name;
                """.format(
                    ",".join(
                        ["('{}',ARRAY[{}]::double precision[],CURRENT_TIMESTAMP)".format(self.read_structure[i[0]],
                                                                                         i[1])
                         for i in frame
                         ])))
            Health[source_name].tmstp = datetime.now()
        except Exception as e:
            self.status = 'down'
            self.stop_flag = True
            log.debug(format_exc())
            log.error('Ошибка записи в базу данных.')

    def start(self):
        """
        Подключение к серверу и запуск чтения значений
        """

        # self.connect_to_server()
        # return self.loop.create_task(self.read())
        pass
        # self.read()

    # def status(self):


if __name__ == "__main__":
    main = ModbusReaderMain()
    main.loop.run_forever()
