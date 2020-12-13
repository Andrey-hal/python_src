from collections import OrderedDict

table_maps = {
    "init": (
        ("№", "n", "n"),
        ("наименование", "description", "s"),
        ("обозначение", "symbol", "s"),
        ("единицы измерения", "units", "s"),
        ("режимы", "value_or_expression", "n"),
        ("кип", "kip", "s"),
    ),
    "others": (
        ("№", "n", "n"),
        ("наименование", "description", "s"),
        ("обозначение", "symbol", "s"),
        ("единицы измерения", "units", "s"),
        ("режимы", "value_or_expression", "nf"),
    ),
    "check": (
        ("№", "n", "n"),
        ("наименование", "description", "s"),
        ("обозначение", "symbol", "s"),
        ("единицы измерения", "units", "s"),
        ("режимы", "value_or_expression", "nf"),
        ("skip", "skip", "nfse"),
        ("skip", "skip", "nfse"),
        ("режимы", "array_check", "nf"),
    ),
    "diagn": (
        ("№", "n", "n"),
        ("наименование", "description", "s"),
        ("имя", "name", "s"),
        ("тип", "data_type", "s"),
        ("условие", "condition", 'fe'),
        ('журнал', 'journal', 'ns')

    ),
    "journal": (
        ("№", "n", "n"),
        ("ссылка", "description_link", "f"),
        ('журнал', 'journal', 'ns')
    )
}


def detect_row_type(row):
    limit = len(row)  # смысл тут в том, что надо из конца "удалить" все нулевые
    for j in row[
             ::-1
             ]:  # ячейки, чтобы потом правильно сравнить кол-во типов ячеек по шаблону
        if not j.value:
            limit -= 1
        else:
            break
    row = row[:limit]
    if not len(row):  # сразу скипаем пустые строки
        return {"type": "empty", "success": True}
    line = [
        p.data_type if p.value is not None else None for p in row
    ]  # тут приходится костылить, ибо у библиотеки
    c_t = {
        "s": 0,
        "n": 0,
        None: 0,
        "f": 0,
        "e": 0,
    }  # тип пустой ячейки такой же, как и у числовой
    for x in set(line):
        c_t[x] += line.count(x)

    if c_t["s"] == 1:  # Title
        value = ""
        for c in row:
            if c.data_type == "s" and len(c.value) > 3:
                value = c.value
                break
        return {"type": "title", "success": True, "title": value, "limit": limit}

    elif c_t["s"] >= 3 and c_t["n"] == 0:  # Шапка
        for mp_name, mp_data in table_maps.items():
            mp = []
            for c in row:
                for v in mp_data:
                    try:
                        if v[0] in c.value.lower():
                            mp.append((v[0], v[1], v[2]))

                    except AttributeError:
                        continue
            if len(mp) == len(row):
                return {"type": "head", "success": True, "map": tuple(mp), "limit": limit}

        if len(mp) != len(row):
            return {
                "type": "head",
                "success": False,
                "error": "head parse error",
                "limit": limit,
            }

    # таблица
    elif c_t["s"] in range(0, 7) and (
            c_t["n"] in range(1, 40) or c_t["f"] in range(0, 40)
    ) and c_t[None] < 2:
        if (
                (c_t["f"] in range(3, 11) or c_t["n"] in range(3, 18))
                and c_t[None] > 4
                and c_t["s"] == 0
        ):
            return {"type": "internal_vars", "success": True, "limit": limit}

        return {"type": "table", "success": True, "limit": limit, 'ds': c_t}

    elif (
            (c_t["f"] in range(3, 11) or c_t["n"] in range(3, 25))
            and c_t[None] > 4
            and c_t["s"] == 0
    ):
        return {"type": "internal_vars", "success": True, "limit": limit}
    elif c_t[None] >= 4 and c_t["n"] <= 1:
        return {"type": "empty", "success": True}
    else:
        return {"type": "None", "success": False, "limit": limit, "t": c_t}
