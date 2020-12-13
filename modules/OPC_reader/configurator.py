#!/usr/bin/env python
"""
Настройка подключения к OPC серверу.
Конфигурация подключения и чтения хранится в configs/opc_reader.ini
Лог сохраняется в logs/reader.log
"""


import OpenOPC
import traceback
from configs import Conf
from time import sleep
import logs

log = logs.logging.getLogger("opc_reader")
log.propagate = False
config = Conf("opc_reader.ini")


class ReadConfiguratorMain:
    """
    Класс создания конфигурации подключения к OPC серверу.
    """

    def __init__(self, ip=None, port=None):
        if 'connection' in config.config:
            user_ip = input('Введите адрес openOPC Gateway в формате "ip:port". Сейчас установлено: {}:{}(enter) \n> '.format(config.config["connection"]['ip'],config.config["connection"]['port']))
        if user_ip != '':
            splited = user_ip.split(':')
            if len(splited) == 2:
                ip = splited[0]
                port = splited[1]
                config.save()
            else:
                print('Формат не распознан, использую значения из конфига')
        else:
            if 'connection' in config.config:
                if ip is None:
                    ip= config.config["connection"]['ip']
                if port is None:
                    port= config.config["connection"]['port']
                print('Использую значения из конфига')
            else:
                print('Неверно введен ip')
                exit(0)

        try:
            self.opc = OpenOPC.open_client(ip, port)
        except:
            log.debug(traceback.format_exc())
            log.critical(
                "Ошибка подключения к openOPC Gateway. Проверьте состояние сервиса zzzOpenOPCService"
            )

            raise SystemExit

        self.server_name = ""
        self.structure = {}
        self.client = self.opc #OpenOPC.client()
        self.servers=self.opc.servers()

    def get_server(self, id=None, name=None):
        '''
        Выбор нужного сервера из списка. Если передать в параметры идентификатор сервера -
        - вернется объект этого сервера.
        :param id: id сервера по списку. Не точно!
        :param name: Название сервера. Точно!
        :return:
        '''
        servers = self.servers

        if id:
            try:
                return servers[id]
            except IndexError:
                return None

        elif name:
            for server in servers:
                if name in server:
                    return server
            return None

        else:
            print('Выберите нужный OPC сервер')
            for n, s in enumerate(servers, start=1):
                print("[{}] - {} {}".format(n, s,'    <- выбран в конфиге' if s == config.config["connection"]["server_name"] else ''))

            while True:
                try:
                    selected_server = servers[int(input("Введите номер: >")) - 1]
                    break
                except ValueError:
                    print("Ошибка при вводе")

            return selected_server

    def connect_to_server(self, server_name=None):
        """
        Подключение к OPC серверу через openOPC Gateway.
        :param server_name: Имя OPC сервера.
        :param server_name:
        :return:
        """
        if not server_name:
            server_name = self.get_server()
        try:
            self.opc.connect(server_name)
            self.client.connect(server_name)
            if self.client.info():
                config.config["connection"]["server_name"] = server_name
                log.info('Успешное подключение к OPC серверу. Записано в конфиг.')
        except:
            log.critical("Ошибка подключения к OPC серверу")
            log.debug(traceback.format_exc())
            return False

        self.server_name = server_name
        return True

    def generate_config(self):
        """
        Создание конфигурационного файла с полученными от пользователя и сервера данными.
        """
        temp_structure = {}

        def recr(item, prefix=[]):
            """
            Рекурсивная функция создания структуры OPC сервера.
            """
            for k, v in item:
                if k == "*":
                    continue
                if type(v) is dict:
                    recr(v.items(), prefix + [k])
                else:
                    config.config["variables"]["/".join(prefix + [k])] = "None"

        recr(self.client.tree(recursive=True).items())
        config.save()


    def start(self):
        self.connect_to_server()
        self.generate_config()
        # self.read()
        # self.get_structure()


if __name__ == "__main__":
    main = ReadConfiguratorMain()
    main.start()
