from json import dumps
from subprocess import Popen, PIPE
import traceback
import requests
from openpyxl import load_workbook, Workbook


def upload_to_php(tables):
    """
    Запускаем php скрипт и кидаем ему через пайп несколько листов. 1 - Спарсенная таблица. 2 - её конфигурация
    Колхоз, конечно. Но куда деваться?.
    """
    try:
        sec_sheet = (
            '{"0":{"0":"table_options","1":"\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b'
            '\u0442\u0430\u0431\u043b\u0438\u0446\u044b","2":null,"3":null,"4":null,'
            '"5":null,"6":null,"7":null},"1":{"0":"id","1":"name_column",'
            '"2":"width","3":"align","4":"type","5":"number_column","6":"vid",'
            '"7":"load"},"2":{"0":"Name","1":null,"2":null,"3":null,'
            '"4":null,"5":null,"6":"value","7":0},"3":{"0":"KIP",'
            '"1":"\u041a\u0418\u041f","2":60,"3":"center","4":"string","5":4,'
            '"6":"value","7":1},"4":{"0":"Description",'
            '"1":"\u041d\u0430\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u043d\u0438\u0435",'
            '"2":200,"3":"left","4":"string","5":3,"6":"value","7":1},'
            '"5":{"0":"Sign",'
            '"1":"\u041e\u0431\u043e\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435","2":100,'
            '"3":"right","4":"string","5":1,"6":"value","7":1},"6":{'
            '"0":"Units","1":"\u0415\u0418","2":60,"3":"center","4":"string",'
            '"5":5,"6":"value","7":1},"7":{"0":"Equation_LaTex",'
            '"1":"\u0424\u043e\u0440\u043c\u0443\u043b\u044b\u043b\u0430\u0442","2":200,'
            '"3":"left","4":"equation","5":2,"6":"value","7":1},"8":{'
            '"0":"Equation","1":"\u0424\u043e\u0440\u043c\u0443\u043b\u044b\u0433\u0440\u0435'
            '\u0447","2":null,"3":null,"4":null,"5":null,"6":"value",'
            '"7":0},"9":{"0":"Value",'
            '"1":"\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u044f","2":70,"3":"center",'
            '"4":"number","5":6,"6":"link(inputvalues.value)","7":1}}'
        )
        frst_sheet = dumps(create_table_configuration(tables))

        data = {'variables':frst_sheet,'config':sec_sheet}
        r = requests.post('http://localhost:8080/it/project1/project1_parse.php', data=data)
        result = (True,) if 'ok' in r.text else (False,{"text": "Ошибка передачи данных в php", "type": "critical", "n": 0})
        return result
    except:
        return (
            False,
            {
                "text": "Ошибка передачи данных в базу",
                "error_type": "critical",
                "n": 0,
                "traceback": traceback.format_exc(),
            },
        )


def create_table_configuration(tables):
    """
    Создаём массив(словарь) для загрузки через php скрипт.
    :rtype: Возвращает массив строк с таблицами и их переменными. Формат: { #Строка:{ #Ячейка:{ } }}
    """
    done = {}
    pattern = {
        "head": {
            "n": {0: "table_n", 1: "null", 2: "table_name"},
            "n+1": {
                0: "Name",
                1: "KIP",
                2: "Description",
                3: "Sign",
                4: "Units",
                5: "Equation_LaTex",
                6: "Equation",
            },
        },
        "table_vars": {
            0: "var_name",
            1: "kip",
            2: "description",
            3: "sign",
            4: "units",
            5: "LaTex",
            6: "equation",
            7: "value",
        },
    }
    line_count = 0

    for table_n, table_name in enumerate(tables, start=1):
        table = tables[table_name]
        temp_row = {n: None for n in range(25)}

        # Шапка 1 строка
        for k, v in pattern["head"]["n"].items():
            value = None
            if v == "table_n":
                value = table_name.replace(' ','').lower()
            elif v == "table_name":
                value = table_name
            else:
                value = None
            temp_row[k] = value

        done[line_count] = temp_row
        line_count += 1

        # Шапка строка 2
        temp_row = {n: None for n in range(25)}

        try:
            values_count = len(list(table["variables"].values())[0]["value"])
        except IndexError:
            continue
        done[line_count] = {
            **temp_row,
            **pattern["head"]["n+1"],
            **{
                k: "Value"
                for k in range(
                    len(pattern["head"]["n+1"]),
                    values_count + len(pattern["head"]["n+1"]),
                )
            },
        }
        line_count += 1

        # Переменные
        for variable_n, variable_data in table["variables"].items():

            temp_row = {n: None for n in range(25)}

            for k, v in pattern["table_vars"].items():
                value = None
                if v == "var_name":
                    value = variable_data["name"]
                elif v == "kip":
                    value = variable_data["kip"]
                elif v == "description":
                    value = variable_data["description"]
                elif v == "sign":
                    value = variable_data["symbol"]
                elif v == "units":
                    value = variable_data["units"]
                elif v == "LaTex":
                    value = variable_data["latex_equation"]
                elif v == "equation":
                    value = variable_data["latex_equation"]
                elif v == "value":
                    for value in variable_data["value"].values():
                        temp_row[k] = value
                        k += 1
                    break
                else:
                    value = None
                temp_row[k] = value

            done[line_count] = temp_row
            line_count += 1

        done[line_count] = {n: None for n in range(25)}
        line_count += 1

    return done
