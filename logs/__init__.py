#!/usr/bin/env python
"""
Модуль логгинга с разделением по файлам для каждого логгера.
"""
import logging
from logging import Handler, StreamHandler
from logging.config import dictConfig
from configs import Conf
import sys
from definitions import *

ROOT_DIR_PROJECT = ROOT_DIR+'\..\..'
config = Conf("config.ini")
file_lvl = config.config['logging']['file_lvl']
console_lvl = config.config['logging']['console_lvl']
dictLogConfig = {
    "version": 1,
    "handlers": {
        "parserfileHandler": {
            "level": file_lvl,
            "class": "logging.FileHandler",
            "formatter": "parserFormatter",
            "filename": ROOT_DIR_PROJECT + "/log/python_parser.log",
            "encoding": "utf-8",
        },
        "parserconsoleHandler": {
            "level": console_lvl,
            "formatter": "parserFormatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "calcfileHandler": {
            "level": file_lvl,
            "class": "logging.FileHandler",
            "formatter": "calcFormatter",
            "filename": ROOT_DIR_PROJECT + "/log/python_calc.log",
            "encoding": "utf-8",
        },
        "calcconsoleHandler": {
            "level": console_lvl,
            "formatter": "calcFormatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "genfileHandler": {
            "level": file_lvl,
            "class": "logging.FileHandler",
            "formatter": "genFormatter",
            "filename": ROOT_DIR_PROJECT + "/log/python_gen.log",
            "encoding": "utf-8",
        },
        "genconsoleHandler": {
            "level": console_lvl,
            "formatter": "genFormatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "readfileHandler": {
            "level": file_lvl,
            "class": "logging.FileHandler",
            "formatter": "readFormatter",
            "filename": ROOT_DIR_PROJECT + "/log/python_reader.log",
            "encoding": "utf-8",
        },
        "readconsoleHandler": {
            "level": console_lvl,
            "formatter": "readFormatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "servicefileHandler": {
            "level": file_lvl,
            "class": "logging.FileHandler",
            "formatter": "serviceFormatter",
            "filename": ROOT_DIR_PROJECT + "/log/python_service.log",
            "encoding": "utf-8",
        },
        "serviceconsoleHandler": {
            "level": console_lvl,
            "formatter": "serviceFormatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "pluginsfileHandler": {
            "level": file_lvl,
            "class": "logging.FileHandler",
            "formatter": "pluginsFormatter",
            "filename": ROOT_DIR_PROJECT + "/log/python_plugins.log",
            "encoding": "utf-8",
        },
        "pluginsconsoleHandler": {
            "level": console_lvl,
            "formatter": "pluginsFormatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "parser": {
            "handlers": ["parserfileHandler", "parserconsoleHandler"],
            "level": "DEBUG",
        },
        "python_calc": {
            "handlers": ["calcfileHandler", "calcconsoleHandler"],
            "level": "DEBUG",
        },
        "gen": {"handlers": ["genfileHandler", "genconsoleHandler"], "level": "DEBUG",},
        "opc_reader": {
            "handlers": ["readfileHandler", "readconsoleHandler"],
            "level": "DEBUG",
        },
        "service": {
            "handlers": ["servicefileHandler", "serviceconsoleHandler"],
            "level": "DEBUG",
        },
        "plugins": {
            "handlers": ["pluginsfileHandler", "pluginsconsoleHandler"],
            "level": "DEBUG",
        },
    },
    "formatters": {
        "parserFormatter": {
            "format": "[parser] | %(asctime)s | %(levelname)s | > %(message)s"
        },
        "calcFormatter": {
            "format": "[python_calc] | %(asctime)s | %(levelname)s | > %(message)s"
        },
        "genFormatter": {
            "format": "[general] | %(asctime)s | %(levelname)s | > %(message)s"
        },
        "readFormatter": {
            "format": "[opc_reader] | %(asctime)s | %(levelname)s | > %(message)s"
        },
        "serviceFormatter": {
            "format": "[service] | %(asctime)s | %(levelname)s | > %(message)s"
        },
        "pluginsFormatter": {
            "format": "[plugins] | %(asctime)s | %(levelname)s | > %(message)s"
        },
    },
}
dictConfig(dictLogConfig)
logging = logging

class bclr:
    HE = '\033[95m'
    OKB = '\033[94m'
    OKG = '\033[92m'
    W = '\033[93m'
    F = '\033[91m'
    C = '\033[0m'
    B = '\033[1m'
    U = '\033[4m'