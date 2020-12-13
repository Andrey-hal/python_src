#!/usr/bin/env python
"""
Инициализация баз данных и нужных для них компонентов.
"""
import logs
from configs import Conf
from datetime import datetime
from pony.orm import *
from traceback import format_exc

log = logs.logging.getLogger("gen")
log.propagate = False
config = Conf("config.ini")

needed = ["provider", "host", "port", "user", "password", "database"]
if not all(i in list(config.config["database"].keys()) for i in needed):
    log.critical(
        "Ошибка конфигурации базы данных. Не найдены параметры: "
        + ",".join(set(needed) - set(config.config["database"].keys()))
    )
    raise SystemExit
db_config = config.config["database"]  # из конфига берем только
