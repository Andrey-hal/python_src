from openpyxl.formula import Tokenizer
from pytexit import py2tex
import logging
import re
from traceback import format_exc
log = logging.getLogger("parser")
log.propagate = False

linest_regex = r"((?P<range>[A-Z]+\d{1,3}\:[A-Z]+\d{1,3})|(?:\d\;)+(?P<d>\d))"
lnst = r"((?P<range>[A-Z]+\d{1,3}\:[A-Z]+\d{1,3})|(?:\d\;)+(?P<d>\d))"
args_regex = r"(?P<range>[^, ].{2,4}:.{2,4}[^;, ])|(?:x(?P<point_x>[A-Z]+[\d]{1,3})y(?P<point_y>[A-Z]+[\d]{1,3}))|(?P<limits>[+-]*[\d][+\-\d% ,.]*)"
trigger_regex = r"(?P<name>(?<==).+(?=\())|(?P<args>(?<=\().*(?=\)))"

column_letters = \
    ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
     "U", "V", "W", "X", "Y", "Z", "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI", "AJ", "AK", "AL",
     "AM", "AN", "AO", "AP", "AQ", "AR", "AS", "AT", "AU", "AV", "AW", "AX", "AY", "BA", "BB", "BC", "BD",
     "BE", "BF", "BG", "BH", "BI", "BJ", "BK", "BL", "BM", "BN", "BO", "BP", "BQ", "BR", "BS", "BT", "BU",
     "BV", "BW", "BX", "BY", "BZ", "CA", "CB", "CC", "CD", "CE", "CF", "CG", "CH", "CI", "CJ", "CK", "CL",
     "CM", "CN", "CO", "CP", "CQ", "CR", "CS", "CT", "CU", "CV", "CW", "CX", "CY", "CZ", "DA", "DB", "DC",
     "DD", "DE", "DF", "DG", "DH", "DI", "DJ", "DK", "DL", "DM", "DN", "DO", "DP", "DQ", "DR", "DS", "DT",
     "DU", "DV", ]

trigger_syn = {'тригер_рабочая_зона': 'trigger_work_area', 'аппрокс': 'linest'}


def expression_decoder_latex_equation(data, variables):
    """
    Преобразование формулы из формата EXCEL в LaTex(mathjax) выражение.
    :param data: Строка, которую надо преобразовать.
    :param variables: Набор переменных, из которых будет составляться выражение.
    :return: строка в синтаксисе LaTex(mathjax)
    """
    done = ""
    to_replace = {"\\times": "\\times ", "$": ""}
    tok = Tokenizer(data)

    for t in tok.items:
        if t.value in "()":
            done += t.value
        elif t.type == "OPERATOR-INFIX":
            done += t.value.replace("^", "**").replace(",", ".")

        elif t.type == "FUNC":
            value = t.value
            if t.subtype == "OPEN":
                to_repl = {"LN": "LOG", "TREND": "trend"}
                for key, val in to_repl.items():
                    value = value.replace(key, val)
                done += value
            else:
                done += value

        elif t.type == "OPERAND" and t.subtype == "RANGE":
            t.value = t.value.replace("$", "")
            n = int("".join(filter(str.isdigit, t.value)))
            if ":" in t.value:
                v = t.value.split(":")
                n = int("".join(filter(str.isdigit, v[0])))
                done += "{}".format(n)
                to_replace[n] = variables[n]["latex_symbol"]

            elif t.value in ["ИСТИНА", "TRUE", "FALSE", "ЛОЖЬ"]:
                continue
            else:
                done += "{}".format(n)
                to_replace[n] = variables[n]["latex_symbol"]

        elif t.type == "OPERAND" and t.subtype == "NUMBER":
            done += str(t.value)
    if not done:
        return ""
    done = py2tex(done, print_latex=False, print_formula=False)
    for k, v in to_replace.items():
        done = done.replace(str(k), str(v))
    return done


def expression_decoder(data):
    """
    Преобразование формулы из формата EXCEL в выполняемою eval строку
    :param data: Выражение, которое нужно преобразовать.
    :return: строка пригодная для выполнения в eval
    """
    done = ""
    tok = Tokenizer(data)
    # param_temp = ""
    # is_trigger = "тригер" in data.lower()
    # try:
    #     if is_trigger:  # Парсинг условия тригера регулярками
    #
    #         args = []
    #         for m in re.finditer(trigger_regex, data, re.MULTILINE):
    #
    #             if m["name"]:
    #                 if m["name"] in trigger_syn:
    #                     done += trigger_syn[m["name"]]
    #                 else:
    #                     log.error("Ошибка парсинга триггера {}. Название не найдено")
    #
    #             if m["args"]:
    #                 done += "("
    #
    #                 for arg in re.finditer(args_regex,m["args"],re.MULTILINE):
    #                     if arg["range"]:
    #                         args.append(
    #                             'dbVar["{}",v]'.format('":"'.join(arg["range"].split(":"))).replace(' ','')
    #                         )
    #
    #                     if arg["point_y"] and arg["point_x"]:
    #                         args.append(
    #                             '{{"x":dbVar["{x}",v],"y":dbVar["{y}",v]}}'.format(
    #                                 y=arg["point_y"], x=arg["point_x"]
    #                             )
    #                         )
    #
    #                     if arg["limits"]:
    #                         for limit_s in arg["limits"].split(","):
    #
    #                             limit_temp = {"p": 1, "c": ''}
    #                             for limit_p in re.finditer(
    #                                     r"(?P<percent>[-+]*[0-9]\d{0,2}(\.\d{1,2})?)%|(?P<digit>[\d,.]+)|(?P<ar>[-+]+)",
    #                                     limit_s,
    #                                     re.MULTILINE,
    #                             ):
    #
    #                                 if limit_p["percent"]:
    #                                     limit_temp["p"] = int(limit_p["percent"]) / 100
    #
    #                                 if limit_p["ar"]:
    #                                     limit_temp["c"] += limit_p["ar"]
    #
    #                                 if limit_p["digit"]:
    #                                     limit_temp["c"] += limit_p["digit"].replace(',','.')
    #                             try:
    #                                 limit_temp['c']=eval(limit_temp['c'])
    #                             except:
    #                                 log.error('Ошибка парсинга аргументов {}'.format(limit_temp['c']))
    #                             args.append(str(limit_temp))
    #
    #         done += ",".join(args) + ")"
    #         return done
    #
    # except Exception as e:
    #     print(format_exc())

    # if "аппрокс" in data:
    #     ranges = []
    #     d = ""
    #     done = "linest("
    #     for m in re.finditer(linest_regex, data, re.MULTILINE):
    #         if m["range"]:
    #             ranges.append('dbVar["{}",v]'.format('":"'.join(m["range"].split(":"))))
    #         if m["d"]:
    #             d = m["d"]
    #     for i in ranges:
    #         done += i + ","
    #     return done + d + ")"

    for t in tok.items:
        if t.value in "()":
            done += t.value
        elif t.type == "OPERATOR-INFIX":
            done += t.value.replace("^", "**")

        elif t.type == "OPERAND" and t.subtype == "RANGE":
            t.value = t.value.replace("$", "")
            if ":" in t.value:

                v = t.value.split(":")
                if len(v) > 2:
                    done += t.value.split(":")[-1]
                    continue
                a = '":"'.join(v)
                done += 'dbVar["{}",v]'.format(a)

            elif t.value in ["ИСТИНА", "TRUE", "FALSE", "ЛОЖЬ"]:
                continue
            else:
                done += 'dbVar["{}",v]'.format(t.value)

        elif t.type == "FUNC":
            value = t.value
            if t.subtype == "OPEN":

                to_replace = {"LN": "LOG", "TREND": "trend", 'АППРОКС': 'approx', 'аппрокс': 'approx'}
                for key, val in to_replace.items():
                    value = value.replace(key, val)
                done += value
            else:
                done += value

        elif t.type == "OPERAND" and t.subtype == "NUMBER":
            done += str(t.value)

        elif t.type == "OPERAND":

            if ":" in t.value:
                done += t.value.split(":")[-1]

        elif t.type == "SEP":
            if t.value == ";":
                done += ","
            else:
                done += t.value
        elif t.type == "ARRAY":
            pass
        else:
            done += t.value

    return done


def create_represent_of_symbol(symbol):
    """
    Создаёт "безопасную" форму строки, исключая из неё русские и специальные символы.
    :param symbol: Строка, которую надо преобразовать.
    :return: "Безопасная" строка
    """
    done_string = ""
    symbols = dict(
        zip(["а", "б", "в", "г", "д", "е", "ё", "ж", "з", "и", "й", "к", "л", "м", "н", "о", "п", "р", "с", "т", "у",
             "ф", "х", "ц", "ч", "ш", "щ", "ъ", "ы", "ь", "э", "ю", "я", "А", "Б", "В", "Г", "Д", "Е", "Ё", "Ж", "З",
             "И", "Й", "К", "Л", "М", "Н", "О", "П", "Р", "С", "Т", "У", "Ф", "Х", "Ц", "Ч", "Ш", "Щ", "Ъ", "Ы", "Ь",
             "Э", "Ю", "Я", "Α", "α", "Β", "β", "Γ", "γ", "Δ", "δ", "Ε", "ε", "Ζ", "ζ", "Η", "η", "Θ", "θ", "Ι", "ι",
             "Κ", "κ", "Λ", "λ", "Μ", "μ", "Ν", "ν", "Ξ", "ξ", "Ο", "ο", "Π", "π", "Ρ", "ρ", "Σ", "σ", "ς", "Τ", "τ",
             "Υ", "υ", "Φ", "φ", "Χ", "χ", "Ψ", "ψ", "Ω", "ω", "·", "(", ")", "'", " ",'"',"'"],
            ["a", "b", "v", "g", "d", "e", "e", "j", "z", "i", "j", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u",
             "f", "h", "z", "c", "s", "s", "_", "y", "_", "e", "u", "a", "A", "B", "V", "G", "D", "E", "E", "J", "Z",
             "I", "J", "K", "L", "M", "N", "O", "P", "R", "S", "T", "U", "F", "H", "Z", "C", "S", "S", "_", "Y", "_",
             "E", "U", "A", "Alph", "alph", "Bet", "bet", "Gam", "gam", "Delt", "delt", "Epsi", "epsi", "Zet", "zet",
             "Eta", "eta", "Thet", "thet", "Lota", "lota", "Kapp", "kapp", "Lambd", "lambd", "Mu", "mu", "Nu", "nu",
             "Xi", "xi", "Omicr", "omicr", "Pi", "pi", "Rho", "rho", "Sigma", "sigma", "sigma", "Tau", "tau", "Upsi",
             "upsi", "Phi", "phi", "Chi", "chi", "Psi", "psi", "Omeg", "omeg", "*", "", "", "", "_",'',"" ], ))
    for i in symbol:
        try:
            done_string += symbols[i]
        except KeyError:
            done_string += i
    number = done_string.count("I")
    if number:
        done_string = done_string.replace("I" * number, str(number))
    return done_string


def create_literal_range(start, stop):
    """
    Генерация буквенного (EXCEL-like) диапазона
    :param start: С какой буквы начать
    :param stop: На какой остановиться
    :return: Буквенный диапазон
    """
    arr = []
    start_flag = False
    start = "".join(filter(str.isalpha, start))
    stop = "".join(filter(str.isalpha, stop))

    for s in column_letters:
        if s == start:
            start_flag = True
        elif s == stop:
            arr.append(s)
            break
        if start_flag:
            arr.append(s)
    return arr


if __name__ == "__main__":
    # tok = Tokenizer("""=ТРИГЕР_РАБОЧАЯ_ЗОНА(E145:S145; E144:S144; xE51yE45; 5%+1; -5% -0,2;5% -0,2;5% +0,2)""")
    # print("\n".join("%12s%11s%9s" % (t.value, t.type, t.subtype) for t in tok.items))
    # print(tok.items.)
    print(
        expression_decoder(
            """=ТРИГГЕР_РАБОЧАЯ_ЗОНА(E145:S145; E144:S144; xE51yE45; 5%+1; -5% -0,2;5% -0,2;5% +0,2)"""
        )
    )
    # print(create_literal_range("M", "R"))
    # print(create_represent_of_symbol('ΔTIIэ'))
