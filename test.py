from libs.service_modules import LocalModule, LocalService

Services = {
    # 'opc_reader': LocalModule(name='opc_reader',
    #                           _module='ReaderMain',
    #                           _import='from modules.OPC_reader.main import ReaderMain',
    #                           active=False,
    #                           need_db=True,
    #                           simulation_stop=True),
    'modbus_reader': LocalModule(name='modbus_reader',
                                 _module='ModbusReaderMain',
                                 _import='from modules.OPC_reader.main import ReaderMain',
                                 active=False,
                                 need_db=True,
                                 simulation_stop=True),
    'python_calc': LocalModule(name='python_calc',
                               _module='CalculationMain',
                               _import='from modules.calculation_module.main import CalculationMain',
                               active=False,
                               need_db=True,
                               simulation_stop=True),
    'db': LocalService(name='db',
                       service_name='PostgreSQL',
                       active=False,
                       need_db=False,
                       simulation_stop=False)
}


class A:
    i = 100

    def __init__(self, *args, **kwargs):
        self.a = args[0]
        self.b = 2
        self.c = self.i
        self.d = kwargs['d']

    def a_sum(self):
        return self.b + self.c


class B(A):
    def a_dif(self, **kwargs):
        self.d = kwargs['d']
        return (self.c - self.b) * self.d


class C(B):
    i = 50
    j = 12

    def a_dif(self, **kwargs):
        super(C, self).a_dif(**kwargs)
        print('C - ' + str(kwargs))
