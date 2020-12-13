import matplotlib.pyplot as plt
import numpy as np
from definitions import ROOT_DIR
from json import dumps
class no_type:
    name = 'Нет типа'

    @staticmethod
    def prnt():
        return 'Нет типа'

    def generate(self,lim=100):
        return [0]*lim

class static:
    name = 'Статичное значение'
    arg_map = {0: {'name': 'значение', 'vr': 'value'}}
    def __init__(self):
        self.value = 0

    def parse(self, s):
        spl = s.split(',')
        if len(spl) != len(static.arg_map):
            raise IndexError('Не совпадает кол-во аргументов')

        args = {n: a for n, a in enumerate(spl) if a not in ['', ' ']}
        for n, arg in args.items():
            setattr(self,static.arg_map[n]['vr'],float(arg.replace(' ','')))
        return self.prnt()

    def prnt(self):
        s = ', '.join(
            ['{}: {}'.format(d['name'], getattr(self,d['vr'])) for n, d in static.arg_map.items()])
        return s

    def generate(self,lim=100):
        return [self.value]*lim


class sin_wave:
    name = 'Синусоида'
    arg_map = {0: {'name': 'период', 'vr': 'n'}, 1: {'name': 'минимальное значение', 'vr': 'mn'},
               2: {'name': 'максимальное значение', 'vr': 'mx'}}

    def __init__(self):
        self.n = 0.1
        self.mn = -1
        self.mx = 1
        self.lim = 20

    @staticmethod
    def d3_scale(dat, out_range=(-1, 1)):
        domain = [np.min(dat, axis=0), np.max(dat, axis=0)]

        def interp(x):
            return out_range[0] * (1.0 - x) + out_range[1] * x

        def uninterp(x):
            b = 0
            if (domain[1] - domain[0]) != 0:
                b = domain[1] - domain[0]
            else:
                b = 1.0 / domain[1]
            return (x - domain[0]) / b

        return interp(uninterp(dat))

    @staticmethod
    def generator(lim=20, n=0.2, min=-1, max=2):
        x = np.arange(0, lim*n, n)
        y = np.sin(x)
        y = sin_wave.d3_scale(y, (min, max))
        return y

    def parse(self, s):
        spl = s.split(',')
        if len(spl) != len(sin_wave.arg_map):
            raise IndexError('Не совпадает кол-во аргументов')

        args = {n: a for n, a in enumerate(spl) if a not in ['', ' ']}
        for n, arg in args.items():
            setattr(self,sin_wave.arg_map[n]['vr'],float(arg.replace(' ','')))
        return self.prnt()

    def prnt(self):
        s = ', '.join(
            ['{}: {}'.format(d['name'], getattr(self,d['vr'])) for n, d in sin_wave.arg_map.items()])
        return s

    def generate(self,lim=100):
        return sin_wave.generator(lim=lim, n=self.n, min=self.mn, max=self.mx)


def show_graph(vars):
    for name,data in vars.items():
        plt.plot(list(range(len(data['data']))),
                 data['data'],
                 label=name)
    plt.xlabel('Время')
    plt.ylabel('Значение')
    plt.title('Сгенерированные данные')
    plt.legend()
    plt.show()

def save_file(vars):
    done = []
    names = vars.keys()
    print(names)
    rn = range(len(list(vars.values())[0]['data']))
    for n in rn:
        predone = {}
        for name in names:
            predone[name]=vars[name]['data'][n]
        done.append(predone)
    with open(ROOT_DIR+'\\modules\\simulator\\data.json','w+') as file:
        file.write(dumps(done))