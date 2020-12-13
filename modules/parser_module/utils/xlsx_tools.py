import zipfile

from modules.parser_module.libs.xmlparser import parse

from modules.parser_module.utils.latex_tools import align_converter

sheet_name = "xl/worksheets/sheet1.xml"
shared_string_name = "xl/sharedStrings.xml"


def parse_file(file):
    sheet = None
    strings = None
    file = zipfile.ZipFile(file, "r")
    if file:
        pass
    else:
        print("error")
    for i in file.filelist:
        i: zipfile.ZipInfo
        name = i.filename

        if sheet_name in name:
            sheet = parse(file.open(name).read(), process_namespaces=False)[
                "worksheet"
            ]["sheetData"]
        elif shared_string_name in name:
            strings = parse(file.open(name).read(), process_namespaces=False)["sst"]
    if sheet is not None and strings is not None:
        return sheet, strings


def format_generator(si):
    done = []
    if "r" not in si:
        if "t" in si:

            try:
                done.append({"type": "default", "text": si["t"]["#text"]})
                return done
            except TypeError:  # Иногда, почему-то, меняется формат
                done.append({"type": "default", "text": si["t"]})
                return done
        else:
            return None

    for r in si["r"]:
        if 'rPr' not in r:
            done.append({"type": "default", "text": r["t"]})
            continue
        try:
            if "vertAlign" in r["rPr"]:
                done.append(
                    {"type": r["rPr"]["vertAlign"]["@val"], "text": r["t"]["#text"]}
                )
            else:
                done.append({"type": "default", "text": r["t"]["#text"]})

        except TypeError:  # Иногда, почему-то, меняется формат
            if "vertAlign" in r["rPr"]:
                done.append({"type": r["rPr"]["vertAlign"]["@val"], "text": r["t"]})
            else:
                done.append({"type": "default", "text": r["t"]})
        except KeyError:
            done.append({"type": "default", "text": r["t"]})
    return tuple(done)


def pars_formated_strings(file):
    tpl = parse_file(file=file)
    sheet = tpl[0]
    strings = tpl[1]
    table = {}

    for row in sheet["row"]:
        n = int(row["@r"])
        table[n] = {}

        if "c" not in row:
            continue
        if type(row["c"]) is not list:
            c = row["c"]
            if "@t" in c and c["@t"] == "s":
                tp = format_generator(strings["si"][int(c["v"])])
                if tp:
                    table[n][c["@r"]] = align_converter(tp)
            continue

        for c in row["c"]:
            # try:

            if "@t" in c and c["@t"] == "s":
                tp = format_generator(strings["si"][int(c["v"])])

                if tp:
                    table[n][c["@r"]] = align_converter(tp)
            # except TypeError:
            #     continue
    return table
