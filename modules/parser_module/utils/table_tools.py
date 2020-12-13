from modules.parser_module.utils import parsing_rules
from modules.parser_module.utils.string_tools import (
    expression_decoder,
    create_literal_range,
    create_represent_of_symbol,
)
from traceback import format_exc


def getCellBorders(cell):
    tmp = cell.border
    brdrs = ""

    if tmp.top.style is not None:
        brdrs += "T"
    if tmp.left.style is not None:
        brdrs += "L"
    if tmp.right.style is not None:
        brdrs += "R"
    if tmp.bottom.style is not None:
        brdrs += "B"
    return brdrs


def table_parsing(sheet):
    """
    Парсим таблицы на листе.
    :param sheet: Лист, с которого будем парсить.
    :return: Словарь вида {'tables':, 'errors':}.
    """
    worksheet = sheet

    # Флаги и переменные
    waiting_for_table = False
    table_name = ""
    table_subname = ""
    last_row_type = ""
    tables = {}
    temp_table = {"variables": {}}
    row_range = {"a": "", "b": ""}

    def join_range_function(d):
        return ":".join(d.values()), {"a": "", "b": ""}

    errors = []
    max_rows = worksheet.max_row

    def create(name, temp_table):
        if name in tables:
            errors.append(
                {
                    "text": "Ошибка! Не уникальное название таблицы!",
                    "error_type": "error",
                    "n": n,
                })
            return
        tables[name] = temp_table

    for n, row in enumerate(worksheet.rows, start=1):  # ⸻
        row_type = parsing_rules.detect_row_type(row)
        if not row_type["success"]:
            errors.append(
                {
                    "text": "Ошибка форматирования таблицы, невозможно распарсить строку",
                    "error_type": "error",
                    "n": 0,
                }
            )
            continue

        if row_type["type"] == "title":

            if waiting_for_table:
                if last_row_type in ["title", "empty"]:
                    table_subname = row_type["title"]
                elif last_row_type in ["table"]:
                    row_range["b"] = row_range["b"] = "{}{}".format(
                        row[temp_table["width"] - 1].column_letter, n - 1
                    )

                    # Заносим таблицу
                    temp_table["range"], row_range = join_range_function(row_range)
                    create(table_name + " " + table_subname, temp_table)
                    temp_table = {"variables": {}}
                    table_subname = row_type["title"]
            else:
                table_name = row_type["title"]
                temp_table["name"] = table_name
                waiting_for_table = True

        elif row_type["type"] == "empty":
            if waiting_for_table:
                if last_row_type == "table":
                    row_range["b"] = "{}{}".format(
                        row[temp_table["width"] - 1].column_letter, n - 1
                    )

                    waiting_for_table = False

                    # Заносим таблицу
                    temp_table["range"], row_range = join_range_function(row_range)
                    create(table_name + " " + table_subname, temp_table)
                    temp_table = {"variables": {}}
                    table_subname = ""

        elif row_type["type"] == "table":

            if waiting_for_table:
                if "width" not in temp_table:
                    temp_table["width"] = row_type["limit"]
                if n == max_rows:  # проверка на конец файла
                    if last_row_type in ["title", "empty", "head"]:
                        row_range["a"] = row[0].coordinate

                    row_range["b"] = "{}{}".format(
                        row[temp_table["width"] - 1].column_letter, n
                    )

                    # Заносим таблицу
                    temp_table["range"], row_range = join_range_function(row_range)
                    create(table_name + " " + table_subname, temp_table)
                    temp_table = {"variables": {}}
                    break
                if last_row_type in ["title", "empty", "head"]:
                    row_range["a"] = row[0].coordinate

                    if (
                        "map" not in temp_table
                    ):  # задаём карту таблицы если она не задалаоась при парсинге
                        if "проверка расч" in table_name.lower():
                            temp_table["map"] = parsing_rules.table_maps["check"]
                            temp_table["type"] = "check"
                        elif "диагноз" in table_name.lower():
                            temp_table["map"] = parsing_rules.table_maps["diagn"]
                            temp_table["type"] = "diagn"
                        elif "журнал" in table_name.lower():
                            temp_table["map"] = parsing_rules.table_maps["journal"]
                            temp_table["type"] = "journal"
                        else:
                            temp_table["map"] = parsing_rules.table_maps["others"]
            else:
                errors.append(
                    {
                        "text": "Ошибка форматирования таблицы. Встречена таблица без названия и(или) шапки {}".format(
                            row_type
                        ),
                        "error_type": "error",
                        "n": n,
                    }
                )

        elif row_type["type"] == "head":
            if waiting_for_table:
                temp_table["map"] = row_type["map"]
                temp_table["width"] = row_type["limit"]
            else:
                errors.append(
                    {
                        "text": "Ошибка форматирования таблицы. Встречена шапка без названия таблицы",
                        "error_type": "error",
                        "n": n,
                    }
                )
        last_row_type = row_type["type"]
    return {"tables": tables, "errors": errors}


def vars_parsing(self):
    """
    Парсим переменные по уже готовым таблицам.
    :param self: родительский класс
    :return: ничего, всё записывается в self.variables
    """
    worksheet = self.sheet
    variables_names = []  # Исключаем повторы названий переменных
    for table_n, (table_name, table) in enumerate(self.tables.items(), start=1):
        last_var = None
        table_rows = worksheet[table["range"]]
        subdomain = ""

        try:
            for row in table_rows:
                var_data = {  # Объект переменной
                    "table_name": table_name,
                    "name": "",
                    "description": "",
                    "subdomain": subdomain,
                    "expression": {},
                    "value": {},
                    "kip": "",
                    "units": "",
                    "symbol": "",
                    "latex_symbol": "",
                    "formulae": "",
                    "need_to_logbox": "0",
                    "condition": "",
                    "data_type": "float",
                }
                waiting_for_subdomain = False

                for n, cell in enumerate(row):
                    data_type = self.sheet_formls[cell.coordinate].data_type
                    cell_value = cell.value
                    last_var = cell.row

                    try:
                        var_map = table["map"][n]
                    except IndexError:
                        pass
                    var_data["row_n"] = cell.row

                    if data_type in var_map[2] and not waiting_for_subdomain:

                        if var_map[1] == "n":
                            waiting_for_subdomain = not cell_value
                            var_data["row_n"] = cell.row

                        elif var_map[1] == "value_or_expression":
                            if data_type == "n":
                                var_data["value"][
                                    cell.column_letter
                                ] = cell.internal_value

                            elif data_type == "f":
                                if type(cell.internal_value) is not str:
                                    var_data["value"][
                                        cell.column_letter
                                    ] = cell.internal_value

                                var_data["expression"][
                                    cell.column_letter
                                ] = expression_decoder(
                                    self.sheet_formls[cell.coordinate].value
                                )

                                var_data["formulae"] = self.sheet_formls[
                                    cell.coordinate
                                ].value

                        elif var_map[1] == "condition":
                            var_data["condition"] = expression_decoder(
                                self.sheet_formls[cell.coordinate].value.replace('$', '')
                            )
                            var_data["value"][cell.column_letter] = 1 if cell_value else 0
                        elif (
                            var_map[1] == "array_check"
                        ):  # Специальный тип таблицы с массивом проверочных данных

                            if data_type == "n":
                                var_data["value"][cell.column_letter] = cell_value

                            elif data_type == "f":

                                var_data["value"][cell.column_letter] = cell_value

                                var_data["expression"][
                                    cell.column_letter
                                ] = expression_decoder(
                                    self.sheet_formls[cell.coordinate].value
                                )

                                var_data["formulae"] = self.sheet_formls[
                                    cell.coordinate
                                ].value

                        elif var_map[1] == "skip":  # если нужно пропустить столбец
                            continue

                        elif var_map[1] == "symbol":  # Обозначение
                            var_data["symbol"] = cell.value

                            var_data["latex_symbol"] = self.latex_formated_strings[
                                cell.row
                            ][cell.coordinate]

                        elif var_map[1] == "description_link":
                            var_data["link"] = int(
                                "".join(
                                    filter(
                                        str.isdigit,
                                        self.sheet_formls[cell.coordinate].value,
                                    )
                                )
                            )

                        elif var_map[1] == "journal":
                            if "link" in var_data:
                                self.variables[var_data["link"]][
                                    "need_to_logbox"
                                ] = cell.internal_value
                                break
                            var_data["need_to_logbox"] = cell.internal_value

                        else:
                            var_data[var_map[1]] = cell.internal_value

                    elif cell.data_type is "s":
                        subdomain = cell_value
                        waiting_for_subdomain = False

                if (
                    var_data and "link" not in var_data
                ):  # Завершаем и записываем переменную в массив
                    if var_data["name"] != "":
                        name = create_represent_of_symbol(var_data["name"])
                    elif (
                        var_data["kip"] == ""
                    ):  # Даём название переменной. Если не по кипу, то по символам
                        name = create_represent_of_symbol(var_data["symbol"])
                        if name.lower() in variables_names:
                            for i in range(1, 20):
                                t = "{}{}".format(name, i)
                                if t.lower() not in variables_names:
                                    name = t
                                    break
                    else:
                        name = var_data["kip"]  # По кипу

                    variables_names.append(name.lower())
                    var_data["name"] = name

                    self.variables[var_data["row_n"]] = var_data  # Пишем в переменные

                    self.tables[table_name]["variables"][
                        var_data["row_n"]
                    ] = self.variables[
                        var_data["row_n"]
                    ]  # И сразу же делаем ссылку в таблицы

        except Exception as e:
            self.make_error(
                "Ошибка в парсинге переменной: {}".format(str(e)),
                "critical",
                last_var,
                traceback=format_exc(),
            )
    return


def array_expressions_parsing(array, sheet):
    """
    Парсим формулы с массивами.
    :param array: сам "массив"
    :param sheet: лист, где расположен сам этот массив
    :return: словарь уже готовых стандартных переменных
    """
    done_vars = {}
    for vrname, vrdata in array.items():
        range = vrdata["ref"].split(":")
        cell = sheet[vrname]
        temp_var = {
            "name": "internal_var[{}]".format(vrname),
            "description": "internal variable",
            "subdomain": "0",
            "expression": {},
            "value": {},
            "kip": "0",
            "row_n": cell.row,
            "units": "0",
        }

        raw_expression = cell.value
        parsd_expression = expression_decoder(raw_expression)
        vrname = int("".join(filter(str.isdigit, vrname)))
        if vrname in done_vars:
            done_vars[vrname]["expression"].update(
                {
                    v: parsd_expression + "[{}]".format(k)
                    for k, v in enumerate(create_literal_range(*range))
                }
            )
        else:
            temp_var.update(
                expression={
                    v: parsd_expression + "[{}]".format(k)
                    for k, v in enumerate(create_literal_range(*range))
                }
            )
            done_vars[vrname] = temp_var
    return done_vars
