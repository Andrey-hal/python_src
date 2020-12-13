from os import system, name
from modules.simulator import tools
def clear():
    # for windows
    if name == 'nt':
        _ = system('cls')

        # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')



def generator_types(n=None):
    sps = [tools.sin_wave, tools.static ,]
    done = []
    if n is None:
        for n,name in enumerate(sps,start=1):
            done.append('#{} {}'.format(n,name.name))
        return '\n'.join(done)
    else:
        return sps[n-1]

class Main:
    def __init__(self):
        self.variables = {}
        self.done = {}

    def create(self):
        variables = []
        while True:
            try:
                entered = input('Введите название переменной:> ')
            except KeyboardInterrupt:
                raise SystemExit
            if '\n' in entered:
                variables.extend(entered.split('\n'))
                print('Введено {} переменных'.format(len(variables)))
                break
            elif '\t' in entered:
                variables.extend(entered.split('\t'))
                print('Введено {} переменных'.format(len(variables)))
                break
            elif ',' in entered:
                variables.extend(entered.split(','))
                print('Введено {} переменных'.format(len(variables)))
                break
            elif ' ' in entered:
                variables.extend(entered.split(' '))
                print('Введено {} переменных'.format(len(variables)))
                break
            else:
                if entered == '':
                    print('Закончен ввод.')
                    break
                variables.append(entered)
        for i in variables:
            self.variables[i]={'type':tools.no_type}

    def var_list(self):
        clear()
        print('Список переменных:')
        for n,(name,data) in enumerate(self.variables.items(),start=1):
            print('#{} {} - {} ({})'.format(n,name,data['type'].name,data['type'].prnt()))

    def edit(self):
        while True:
            self.var_list()
            while True:
                try:

                    ind = input('Введите номер переменной:>')
                    var_n = int(ind) - 1
                    var_name = list(self.variables)[var_n]
                    var_data = self.variables[var_name]
                    break
                except ValueError:
                    if ind == '':
                        print('Ввод закончен')
                        return
                    print('Ошибка','Введите число')
                except IndexError:
                    print('Ошибка','Введите число из списка выше')
                except KeyboardInterrupt:
                    raise SystemExit
            clear()
            print('Изменяем: {} - {}'.format(var_name,var_data['type'].prnt()))
            print('Выберите тип:')
            print(generator_types())
            while True:
                try:

                    gen_n = int(input('Введите номер типа:>'))
                    gen_type = generator_types(gen_n)
                    break
                except ValueError:
                    print('Ошибка','Введите число')
                except IndexError:
                    print('Ошибка','Введите число из списка выше')
                except KeyboardInterrupt:
                    raise SystemExit
            print('Выбран {}'.format(gen_type.name))
            self.variables[var_name]['type']=gen_type()
            while True:
                args = input('Введите строку конфигурации в формате(только значения через запятую по порядку):\n "{}"\n:?> '.format(
                    self.variables[var_name]['type'].prnt()))

                try:
                    result =  self.variables[var_name]['type'].parse(args)
                except IndexError as e:
                    print('Ошибка',e)
                    continue

                print(result)
                rep = False if input('Всё верно:?> ') in 'Yesyes Дада' else True
                if rep:
                    continue
                else:
                    break

    def generate(self):
        clear()
        while True:
            try:
                lm = int(input('Введите кол-во семплов(секунд):?> '))
                break
            except:
                print('Не число')
        for name, data in self.variables.items():
            print('Генерируем {}...'.format(name))
            self.variables[name]['data']=data['type'].generate(lm)


        tools.show_graph(self.variables)
    def start(self):
        print('''Краткое описание управления:
1. Переменные можно вводить как последовательно, так и с разделителями в виде запятой, пробела, табуляции. Допустима вставка из EXCEL
2. Ввод заканчивается нажатием Enter''')
        self.create()
        self.edit()
        self.generate()
        tools.save_file(self.variables)

if __name__ == "__main__":
    Main().start()