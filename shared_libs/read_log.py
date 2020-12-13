"""
Модуль парсинга файла лога.
лог должен быть в формате [Modulename] | %(asctime)s | %(levelname)s | > %(message)s + [доп название модуля]
"""
import re

regex = r"(?P<module>(?<=\[)\w+(?=\]))|(?P<date>(?:\d{1,4}[-]*)+ *(?:\d{2,3}[:,]*)*)|(?P<lvl>INFO|DEBUG|WARNING|ERROR|CRITICAL)|\>.*(?P<service>(?<=\[)\w+(?=\]))|(?P<data>(?<=\>).*$)"


def parse_log_line(test_str):
    a = {}
    for m in re.finditer(regex, test_str, re.MULTILINE):
        for k, v in m.groupdict().items():
            if v:
                a[k] = v
    return a


def read_log(file, lines=100, lvl=None):
    if lvl is None:
        lvl = ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]
    elif type(lvl) is str:
        lvl = list(lvl)

    with open(file, "r", encoding="utf-8") as fin:
        s = 0
        while fin.readline():
            s += 1
        fin.seek(0)
        mylines = []
        temp_lines = []
        for i, e in enumerate(fin):
            try:
                if i >= s - lines:
                    parsed = parse_log_line(e)
                    if len(parsed) > 1:
                        if parsed['lvl'] not in lvl:
                            temp_lines = []
                            continue
                        temp_lines.insert(0, e.replace("\n", ""))
                        parsed.update(text="\n".join(temp_lines))
                        mylines.append(parsed)
                        temp_lines = []
                    else:
                        temp_lines.insert(0, e.replace("\n", ""))
            except:
                continue
    return mylines
