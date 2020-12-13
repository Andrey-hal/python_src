#!/usr/bin/env python
"""
Хранилище конфигурации для всего проекта.
"""
import configparser
from traceback import format_exc

import logging
from definitions import *

log = logging.getLogger("gen")

ROOT_DIR_PROJECT = ROOT_DIR+'\..\..'
class Conf:
    """
    Класс для работы с файлами конфигурации(чтение, запись, хранение в памяти).
    """
    def __init__(self, name):
        self.name = name
        self.config = configparser.ConfigParser()
        self.config.optionxform = str  # Убираем чувствительность к регистру
        try:
            self.readFile()
        except:
            log.error("Ошибка чтения/создания файла конфигурации {}".format(self.name))
            log.debug("^ {}".format(format_exc()))
            raise SystemExit

    def readFile(self, file=None):
        """
        Чтение файла конфигурации.
        :param file: имя файла
        """
        if not file:
            file = self.name

        if not self.config.read(ROOT_DIR_PROJECT + "/config/" + file,encoding='utf-8'):
            with open(ROOT_DIR_PROJECT + "/config/" + file, "w",encoding='utf-8') as configfile:
                self.config.write(configfile)

    def save(self):
        """
        Сохранения файла конфигурации.
        """
        try:
            with open(ROOT_DIR_PROJECT + "/config/" + self.name, "w",encoding='utf-8') as configfile:
                self.config.write(configfile)
        except:
            log.error("Ошибка записи файла конфигурации {}".format(self.name))
            log.debug("^ {}".format(format_exc()))

