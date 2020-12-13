# !/usr/bin/env python
"""
Модуль расчёта переменных. Включает в себя получение данных, расчёт и загрузку результатов
в базу данных.
"""
from time import sleep
from threading import Thread
from traceback import format_exc
import asyncio
from logs import logging
from models.local_db import *
from models.work_db import *
from modules.calculation_module.helpers import *
from shared_libs.custom_math import  *

tm_g = datetime.now()
log = logging.getLogger("python_calc")
log.propagate = False

source_name = "python_calc"


class CalculationMain:
    """
    Модуль чтения, расчётов и записи перменных.
    """

    @db_session
    def __init__(self, loop=None):
        # if loop is None:
        #     loop = asyncio.get_event_loop()
        self.loop = asyncio.get_event_loop()
        self.pause = False
        self.stop_flag = False
        self.status = "starting"
        self.log = log

        # Подгружаем из локальной базы переменные
        self.local_vars = {
            v.row_n: dict(
                name=v.name,
                row_n=v.row_n,
                value=dict(v.value)
                if v.static or len(v.expression) < len(v.value) else {},
                  # Проверки на статичность перменных или имеет ли она данные, нужные дла рсчёта
                condition=False if v.condition == "" else v.condition,
                expression={
                    k: compile(v, "<string>", "eval")
                    for k, v in v.expression.items()
                },  # dict(v.expression.items())
                static=v.static,
                need_to_logbox=v.need_to_logbox,
                data_type=v.data_type,
                symbol=v.symbol,
                units=v.units,
                description=v.description
            )
            for v in select(var for var in Variable)
        }

        # Задаем переменные, которые будем подгружать из рабочей базы
        self.input_variables = {
            i.name: i.row_n
            for i in select(b for b in Table if 'Измеренные параметры' in b.name).first().variables
        }
        self.check_db()

        self.triggers = []
        self.frame = {}

    def check_db(self):
        succ = True
        live = {i.name: i for i in select(v for v in VariableWork)}
        for row_n, local_var in self.local_vars.items():
            local_name = local_var["name"]

            if local_name not in live:
                if "internal_var" in local_name:
                    continue
                succ = False
                log.critical(
                    "Несоответствие переменных: {} не найдена в рабочей базе".
                        format(local_name))
                continue

            if local_name not in self.input_variables:
                if live[local_name].source in [None, ""]:
                    log.info(
                        "Переменная {} не имеет признак источника, присваиваю себе."
                            .format(local_name))
                    live[local_name].source = source_name

                elif live[local_name].source != source_name:
                    succ = False
                    log.critical(
                        "Несоответствие переменных: {} уже присвоена другому источнику({}), не могу "
                        "использовать её для записи".format(
                            local_name, live[local_name].source))

            if local_var["need_to_logbox"] != live[local_name].need_to_logbox:
                if live[local_name].need_to_logbox == 2:
                    log.info(
                        "Атрибут изменён: у переменной {} изменился атрибут записии в историю на 2"
                    )

                if live[local_name].need_to_logbox == 1:
                    log.info(
                        "Атрибут изменён: у переменной {} изменился атрибут записии в историю на 1"
                    )
                    local_var["need_to_logbox"] = live[
                        local_name].need_to_logbox
                    Variable.get(
                        row_n=row_n
                    ).need_to_logbox = live[local_name].need_to_logbox

                if live[local_name].need_to_logbox in [0, "", None]:
                    log.info(
                        "Атрибут изменён: у переменной {} изменился атрибут записии в историю на 0"
                    )
                    local_var["need_to_logbox"] = live[
                        local_name].need_to_logbox
                    Variable.get(
                        row_n=row_n
                    ).need_to_logbox = live[local_name].need_to_logbox

            try:
                Health[source_name]
            except pony.orm.core.ObjectNotFound:
                log.info('Отсутвует переменная состояния. Создание...')
                Health(name=source_name, type='service')

        if not succ:
            log.critical("Ошибка инициализации, выход...")
            raise SystemExit("Ошибка инициализации, выход...")

    def check_db_alive(self):
        while True:
            try:
                with db_session:
                    Health[source_name]
                    return True
            except:
                pass
            sleep(1)

    async def get_updates(self):
        """
        Цикл ожидания обновлений переменных в рабочей базе.
        :return: Возвращает переменные с актуальными входными данными.
        """
        global tm_g  # DEBUG

        while True:
            # Блок управления потоком
            if self.pause:
                self.status = 'paused'
                await asyncio.sleep(1)
                continue
            if self.stop_flag:
                if self.status == 'down':
                    log.error('Упала база, ожидание подключения...')
                    result = await self.loop.run_in_executor(None, self.check_db_alive)
                    if result:
                        log.info('Подключение возобновлено, продолжение работы.')
                        self.stop_flag = False
                        continue
                    else:
                        await asyncio.sleep(1)
                        continue
                self.status = 'stopped'
                break

            variables = self.input_variables
            try:
                with db_session:
                    data = select(i for i in VariableWork
                                  if i.name in list(variables.keys()))
                    tm_g = datetime.now()  # DEBUG
                    work_variables = {v.name: v.flo[0] for v in data}
            except:
                self.status = 'down'
                self.stop_flag = True
                log.error('Ошибка записи в базу данных.')
                log.debug(format_exc())
                continue

            if self.frame == work_variables:  # Проверка состояния обновления входных данных
                await asyncio.sleep(0.4)  # TODO сделать конфигурацию задержки
                continue
            else:
                try:
                    temp_vars = self.local_vars.copy()
                    for k, v in variables.items():
                        temp_vars[v]["value"][next(
                            iter(
                                temp_vars[v]["value"].keys()))] = work_variables[k]
                    self.frame = work_variables
                    await self.calculate(temp_vars)
                except:
                    log.error(format_exc())

    async def calculate(self, v, standalone=False):
        """

        :param v: Входное поле переменных
        :return: расчитанные переменные
        """

        try:
            calculated = {}
            calculated_logbox = {}
            tm = datetime.now()  # DEBUG
            for row_n, var in v.items():
                values = {}
                # if var["static"]:
                #     continue
                if var["expression"]:
                    for name, expression in var["expression"].items():
                        try:

                            # values = {k: vl for k, vl in var['value'].items() if vl is not None}
                            values[name] = eval(expression)

                        except IndexError:
                            pass  # polyfit возвращает меньше значений, чем размер массива в экселе. Это нормально.
                        except ZeroDivisionError:
                            log.error(
                                "Деление на 0 в переменной {}, выражение {}".
                                    format(var["name"], expression))
                        except:
                            log.critical(
                                "Неизвестная ошибка(смотри лог) при вычислении переменной {}, выражение {}"
                                    .format(var["name"], expression))
                            log.debug(format_exc())

                elif var['condition']:
                    try:
                        if 'E' in var['value']:
                            previous = var['value']['E']
                        else:
                            previous = None

                        values['E'] = eval(var['condition'])
                        if type(values['E']) is bool:
                            values['E'] = 1 if values['E'] else 0
                        if previous is not None:
                            if previous != values['E']:
                                calculated_logbox[var["name"]] = {'value': values['E'], 'description':var['description']}


                    except ZeroDivisionError:
                        log.error(
                            "Деление на 0 в переменной {}, выражение {}".
                                format(var["name"], var['condition']))
                    except:
                        log.critical(
                            "Неизвестная ошибка(смотри лог) при вычислении переменной {}, выражение {}"
                                .format(var["name"], var['condition']))
                        log.debug(format_exc())

                elif var["static"]:
                    continue
                calculated[var["name"]] = {'data_type': var['data_type'], 'values': values,
                                           'logbox': var['need_to_logbox']}
                v[row_n]["value"].update(values)

            log.debug("На расчёт {} переменных ушло {}".format(
                len(calculated),
                (datetime.now() - tm).microseconds * 1e-6))

            if standalone:
                return calculated
            self.loop.run_in_executor(None, self.upload_all_variables, calculated)
            self.loop.run_in_executor(None, self.upload_logtable_variables, calculated_logbox)

        except:
            log.error("Ошибка при расчётах")
            log.error(format_exc())

    def upload_logtable_variables(self, values):
        try:
            with db_session:
                for k, v in values.items():
                    Logtable(variablework_name=k, value=v['value'], archived=0, log_date=datetime.now(),
                             description='test')
        except:
            self.status = 'down'
            self.stop_flag = True
            log.error("Ошибка записи в рабочую базу данных(смотри лог)")
            log.debug(format_exc())

    def upload_all_variables(self, values):
        tm = datetime.now()  # DEBUG
        arr = []
        for k, v in values.items():
            if v is not None:

                arr.append("('{name}',ARRAY[{values_flo}]::double precision[],CURRENT_TIMESTAMP)".format(name=k,
                                                                                              values_flo=",".join(
                                                                                                  map('{:f}'.format,
                                                                                                      v[
                                                                                                          'values'].values()))))


        try:
            with db_session():
                work_db.execute("""update variablework as v set flo = c.flo, tmstp = c.tmstp
                    from (values {} ) as c(name, flo, tmstp) 
                    where c.name = v.name;
                    """.format(",".join(arr)))
                Health[source_name].tmstp = datetime.now()

            self.status = 'ok'
            log.debug("На запись ушло {}".format(
                (datetime.now() - tm).microseconds * 1e-6))
        except:
            self.status = 'down'
            self.stop_flag = True
            log.error("Ошибка записи в рабочую базу данных(смотри лог)")
            log.error(format_exc())

    def start(self):
        return self.loop.create_task(self.get_updates())


if __name__ == "__main__":
    print('wtf')
    main = CalculationMain()
    main.start()

    main.loop.run_forever()
