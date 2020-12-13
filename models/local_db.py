#!/usr/bin/env python
"""
Локальная база данных. Предназначена для хранения необходимых для парсинга и расчётов данных.
"""
from models import *
from definitions import *
local_db = Database()
local_db.bind(provider="sqlite", filename=ROOT_DIR+"/data/database.sqlite", create_db=True)


class Table(local_db.Entity):
    """
    Таблица с полученными при парсинге таблицами переменных.
    """
    id = PrimaryKey(int, auto=True)
    name = Optional(str)
    variables = Set("Variable")
    range = Optional(str)
    map = Optional(Json)
    width = Optional(int)
    type = Optional(str)


class Variable(local_db.Entity):
    """
    Таблица с полученными при парсинге переменными.
    """
    row_n = Required(int)
    name = Required(str)
    description = Optional(str)
    value = Optional(Json)
    expression = Optional(Json)
    symbol = Optional(str)
    units = Optional(str)
    kip = Optional(str)
    latex_symbol = Optional(str)
    subdomain = Optional(str)
    table = Optional(Table)
    static = Optional(bool, default=True)
    updated = Optional(datetime, default=lambda: datetime.now())
    fresh = Optional(bool, default=False)
    condition = Optional(str)
    need_to_logbox = Optional(int)
    data_type = Optional(str)
    PrimaryKey(row_n, name)




local_db.generate_mapping(create_tables=True)
