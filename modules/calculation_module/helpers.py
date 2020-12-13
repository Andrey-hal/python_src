from math import log as LOG
from shared_libs.custom_math import *

def getArray(dict, key):
    return list(map(dict, key))


class A(type):
    """
    Класс для работы с переменными которые обращаются из eval строки.
    """

    @staticmethod
    def __getitem__(item):
        (
            item,
            v,
        ) = item  # Принимаем мы на вход два параметра [Id/слайс, v], где v - массив актуальных переменных

        if type(item) == str:
            """
            Если в параметре строка - возвращаем элемент массива.
            """
            row, key = "", ""

            for c in item:
                if c.isdigit():
                    row += c
                else:
                    key += c
            row = int(row)
            var = v[row]

            if key == "":
                key == var.value.keys()[0]

            if var.static:
                return var.value[key]
            else:
                if key in var.value:
                    return var.value[key]
                else:

                    return eval(var.expression[key])

        elif type(item) == int:
            """
            Если в параметре только число - вероятнее всего нужно вернуть только первое значение из массива.
            """
            var = v[item].value

            if var.static:
                return (var.value.values())[0]
            else:
                return list(var.expression.values())[0]

        elif type(item) == slice:
            """
            Если принимаем в параметр слайс, то нужно будет вернуть "разрез" массива.
            """
            start = item.start
            stop = "".join(filter(str.isalpha, item.stop))
            row = int("".join(filter(str.isdigit, start)))
            start = "".join(filter(str.isalpha, start))
            var = v[row]

            # Тут собираем массив, учитывая ключи начала и конца.
            # Т.е. если передали слайс ['B1':'E1'], то мы возьмём из массива только данные под ключами B,C,D,E
            tmp_value = []
            flag = False

            for k, v in var.value.items():
                if k == start:
                    flag = True
                elif k == stop:
                    tmp_value.append(v)
                    break
                if flag:
                    tmp_value.append(v)

            return tmp_value


class dbVar(object, metaclass=A):
    """
    Создаём прокси для основного класса, чтобы принимать запросы без инициализации класса.
    """

    pass
