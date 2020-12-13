#!/usr/bin/env python
"""
Модель рабочей базы данных. Подключение настраивается файлом общей конфигурации.
"""
from models import *
from datetime import time

work_db = Database()

try:
    work_db.bind(
        provider=db_config["provider"],
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
    )
except Exception as exp:

    if "does not exist" in str(exp):
        if "database" in str(exp):
            log.info("База {} не существует, создание...".format(db_config["database"]))
            try:
                import psycopg2

                conn = psycopg2.connect(
                    dbname="postgres",
                    user=db_config["user"],
                    port=db_config["port"],
                    host=db_config["host"],
                    password=db_config["password"],
                )
                conn.autocommit = True
                cur = conn.cursor()
                cur.execute("CREATE DATABASE {};".format(db_config["database"]))
                log.info("База создана")
            except:
                log.critical("Ошибка создания базы!")
                log.debug(format_exc())
                raise ConnectionError
    elif 'Connection refused' in str(exp):
        log.critical("Невозможно подключиться к базе данных. Возможна она не запущена или неправильно указаны "
                     "настройки подключения.")
        raise ConnectionError
    else:
        log.critical("Неизвестная ошибка иниациализации базы данных")
        log.debug(format_exc())
        raise ConnectionError

    work_db.bind(
        provider=db_config["provider"],
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        timeout=1
    )


class VariableWork(work_db.Entity):
    """
    Модель главной таблицы рабочей базы.
    """

    _table_ = (db_config["scheme"], "variablework")
    id = PrimaryKey(int, auto=True)
    name = Optional(str, unique=True)
    internal = Optional(str)
    description = Optional(str)
    sign = Optional(str)
    units = Optional(str)
    type = Optional(str)
    is_array = Optional(bool)
    flo = Optional(FloatArray)
    strng = Optional(StrArray)
    bool = Optional(bool)
    source = Optional(str)
    tmstp = Optional(datetime, sql_default="CURRENT_TIMESTAMP")
    need_to_logbox = Optional(int)


class Logtable(work_db.Entity):
    _table_ = (db_config["scheme"], "logtable")
    id = PrimaryKey(int, auto=True)
    log_date = Optional(datetime, sql_default="CURRENT_TIMESTAMP")
    archive_date = Optional(datetime)
    variablework_name = Optional(str)
    value = Optional(int)
    archived = Optional(int)
    description = Optional(str)
    archive_user_name = Optional(str)
    read_date = Optional(datetime)
    read_user_name = Optional(str)


class Health(work_db.Entity):
    _table_ = (db_config["scheme"], "health")
    name = PrimaryKey(str)
    tmstp = Optional(datetime, sql_default="CURRENT_TIMESTAMP")
    value = Optional(str)
    type = Optional(str)
    params = Optional(Json,default={'period':10})  # {'period':10}


work_db.generate_mapping(create_tables=True)
