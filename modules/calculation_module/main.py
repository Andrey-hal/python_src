# !/usr/bin/env python
"""
Модуль расчёта переменных. Включает в себя получение данных, расчёт и загрузку результатов
в базу данных.
"""
from time import sleep
from threading import Thread
from traceback import format_exc
import asyncio
import socket
from logs import logging
from models.local_db import *
from models.work_db import *
from modules.calculation_module.helpers import *
from shared_libs.custom_math import *

source_name = "python_calc"


class prepared_Variable:
    def __init__(self, var_object):
        self.name = ''
        self.row_n = None

        self.type = []
        self.data_type = 'float'
        self.static = True

        self.value = {}
        self.expression = {}
        self.expression_compiled = {}
        self.condition = ''
        self.condition_value = None

        self.logbox = 0

        self.symbol = ''
        self.units = ''
        self.description = ''

        self.calculation_time = 0
        self.var_object = var_object
        self._create()

    def _create(self):
        self.name = self.var_object.name
        self.row_n = self.var_object.row_n

        self.value = dict(self.var_object.value)

        self.expression = dict(self.var_object.expression)
        self.expression_compiled = {
            k: compile(v, "<string>", "eval")
            for k, v in self.expression.items()
        }

        self.condition = self.var_object.condition

        if self.value:
            self.type.append('value')
        if self.expression:
            self.type.append('expression')
            self.static = False
        if self.condition:
            self.type.append('condition')
            self.static = False

        self.logbox = self.var_object.need_to_logbox

        self.symbol = self.var_object.symbol
        self.units = self.var_object.units
        self.description = self.var_object.description

    def calculate(self, v):
        done_value = {}
        done_condition = None
        to_return = {}
        calc_start_time = datetime.now()
        if 'expression' in self.type:
            for k, expression in self.expression_compiled.items():
                try:
                    done_value[k] = eval(expression)
                except IndexError:
                    pass  # polyfit возвращает меньше значений, чем размер массива в экселе. Это нормально.
                except KeyError as exp:
                    raise KeyError(
                        '''Переменная ссылается на несуществующую переменную #{exception} {self.name} {expression}'''.
                            format(self=self, expression=expression, exception=exp))

                except:
                    raise SyntaxError(
                        '''Ошибка вычисления переменной #{self.row_n} {self.name} {expression}\n{exception}'''.
                            format(self=self, expression=expression, exception=format_exc))
            self.value.update(done_value)
            to_return['value'] = list(done_value.values())

        if 'condition' in self.type:
            try:
                done_condition = 1 if eval(self.condition) else 0
            except:
                raise SyntaxError(
                    '''Ошибка вычисления переменной диагноза {self} {condition}\nОшибка:\n{exception}'''.
                        format(self=self, condition=self.condition, exception=format_exc()))

            if done_condition != self.condition_value:
                to_return['condition'] = done_condition
                self.condition_value = done_condition

        self.calculation_time = datetime.now() - calc_start_time
        return to_return

    def set_first_value(self, value):
        key = list(self.value.keys())[0]
        self.value[key] = value

    def __repr__(self):
        return 'Переменная #{self.row_n} {self.name} <value: {self.value},\n expression: {self.expression}\n ' \
               'condition: {self.condition} = {self.condition_value},\n время расчёта: {self.calculation_time},' \
               ' type:{self.type} > '.format(self=self)


class CalculationMain:
    """
    Модуль чтения, расчётов и записи перменных.
    """

    def __init__(self, loop=None):
        self.loop = asyncio.get_event_loop()

        self.pause = False
        self.stop_flag = False
        self.status = "starting"
        self.log = log
        self.variables = None
        self.input_variables = None

        try:
            self.get_var_configuration()
        except:
            self.status = "down"
            self.stop_flag = True
            return

        self.triggers = []
        self.frame = {}

    @db_session
    def get_var_configuration(self):
        self.variables = {
            local_var.row_n: prepared_Variable(local_var)
            for local_var in select(var for var in Variable)
        }

        self.input_variables = {
            i.name: i.row_n
            for i in select(b for b in Table if 'Измеренные параметры' in b.name).first().variables
        }

    @db_session
    def check_config(self):
        success = True
        live = {i.name: i for i in select(v for v in VariableWork)}

        for row_n, local_var in self.variables.items():
            local_name = local_var.name

            if local_name not in live:
                if "internal_var" in local_name:
                    continue
                success = False
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
                    success = False
                    log.critical(
                        "Несоответствие переменных: {} уже присвоена другому источнику({}), не могу "
                        "использовать её для записи".format(
                            local_name, live[local_name].source))

            if local_var.logbox != live[local_name].need_to_logbox:
                if live[local_name].need_to_logbox == 2:
                    log.info(
                        "Атрибут изменён: у переменной {} изменился атрибут записии в историю на 2"
                    )

                if live[local_name].need_to_logbox == 1:
                    log.info(
                        "Атрибут изменён: у переменной {} изменился атрибут записии в историю на 1"
                    )
                    local_var.logbox = live[
                        local_name].need_to_logbox
                    Variable.get(
                        row_n=row_n
                    ).need_to_logbox = live[local_name].need_to_logbox

                if live[local_name].need_to_logbox in [0, "", None]:
                    log.info(
                        "Атрибут изменён: у переменной {} изменился атрибут записии в историю на 0"
                    )
                    local_var.logbox = live[
                        local_name].need_to_logbox
                    Variable.get(
                        row_n=row_n
                    ).need_to_logbox = live[local_name].need_to_logbox

            try:
                Health[source_name]
            except pony.orm.core.ObjectNotFound:
                log.info('Отсутвует переменная состояния. Создание...')
                Health(name=source_name, type='service')

        if not success:
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

    async def work_control(self):
        while True:
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
                        return
                    else:
                        await asyncio.sleep(1)
                        continue
                self.status = 'stopped'
                return 'break'
            return

    async def get_updates(self):
        """
        Цикл ожидания обновлений переменных в рабочей базе.
        :return: Возвращает переменные с актуальными входными данными.
        """
        global tm_g  # DEBUG
        while True:
            # Блок управления потоком
            if await self.work_control() == 'break':
                break
            else:
                pass

            try:
                with db_session:
                    data = select(i for i in VariableWork
                                  if i.name in list(self.input_variables.keys()))
                    tm_g = datetime.now()  # DEBUG
                    live_data = {v.name: v.flo[0] for v in data}
            except:
                self.status = 'down'
                self.stop_flag = True
                log.error('Ошибка чтения живых данных из базы данных\n{}'.format(str(format_exc())))
                continue

            if self.frame == live_data:  # Проверка состояния обновления входных данных
                await asyncio.sleep(0.4)  # TODO сделать конфигурацию задержки
                continue
            else:
                try:
                    for name, v in live_data.items():
                        row = self.input_variables[name]
                        variable = self.variables[row]
                        variable.set_first_value(v)
                    await self.calculate()
                    self.frame = live_data
                except:
                    log.error('Ошибка запуска итерации расчётов с данными {}. Пропуск итерации.\n{}'.
                              format(live_data, str(format_exc())))

    async def calculate(self):
        to_upload = {'value': {}, 'condition': {}}
        calc_time = datetime.now()
        for row_n, variable in self.variables.items():
            try:
                calculated = variable.calculate(self.variables)
            except:
                log.error('Ошибка рассчёта переменной {}\n{}'.format(variable, format_exc()))
                continue
            if 'value' in calculated:
                to_upload['value'].update({variable.name: {'value': calculated['value'], 'row_n': variable.row_n}})
                # to_upload['value'].update({variable.name: {'value': calculated['value']}}) ---
            if 'condition' in calculated:
                to_upload['condition'].update({variable.name:
                                                   {'value': calculated['condition'],
                                                    'description': variable.description}
                                               })
        log.debug('Расчёт завершён за {}'.format(datetime.now() - calc_time))
        self.loop.run_in_executor(None, self.upload, to_upload)
        self.loop.run_in_executor(None, self.uploadVACS, to_upload)

    def upload(self, data):
        values_prepared = []
        try:
            for k, v in data['value'].items():
                if v is not None:
                    values_prepared.append("('{name}',ARRAY[{values_flo}]::double precision[],CURRENT_TIMESTAMP)".
                                           format(name=k, values_flo=",".join(
                        map('{:f}'.format, v['value']))
                                                  )
                                           )
        except:
            log.error("Ошибка записи в рабочую базу данных.\n{}".format(format_exc()))

        try:
            with db_session():
                work_db.execute("""update variablework as v set flo = c.flo, tmstp = c.tmstp
                    from (values {} ) as c(name, flo, tmstp) 
                    where c.name = v.name;
                    """.format(",".join(values_prepared)))
                Health[source_name].tmstp = datetime.now()

                for k, v in data['condition'].items():
                    Logtable(variablework_name=k, value=v['value'], archived=0, log_date=datetime.now(),
                             description=v['description'])
            self.status = 'ok'
        except:
            self.status = 'down'
            self.stop_flag = True
            log.error("Ошибка записи в рабочую базу данных.\n{}".format(format_exc()))

    def uploadVACS(self, data):
        sock = socket.socket()
        sock.connect(('localhost', 33455))
        values_prepared = []
        for name, value in self.frame.items():
            values_prepared.append('dst=db;box=1;var={name};val={values_flo};err=0@'.
                                   format(name=self.input_variables[name], values_flo=value)
                                   )
        for k, v in data['value'].items():
            if v is not None and len(v['value']) == 1:
                values_prepared.append('dst=db;box=1;var={name};val={values_flo};err=0@'.
                                       format(name=v['row_n'], values_flo=v['value'][0])
                                       )
        try:
            for s in values_prepared:
                sock.send(s.encode())
        except:
            log.error("Ошибка записи в базу данных ВАКС.\n{}".format(format_exc()))
        sock.close()
        f = open('conf.txt', 'w')
        for var in self.variables.values():
            if len(var.value) == 1:
                f.write('{}\t\t {}\n'.format(var.row_n, var.name))
        f.close()

    def start(self):
        return self.loop.create_task(self.get_updates())


if __name__ == "__main__":
    main = CalculationMain()
    main.start()

    main.loop.run_forever()
