from json import loads,dumps


class Json_Type:
    def __init__(self, file):
        self.file = file
        try:
            self.parsed = loads(file.read())
        except:
            raise TypeError("Файл не соответствует формату json")
        self.type = type(self.parsed)
        if self.type is dict:
            self.min = int(min(self.parsed)) if len(self.parsed) else 0
            self.max = int(max(self.parsed)) if len(self.parsed) else 0
        elif self.type is list:
            self.min = 0
            self.max = len(self.parsed)
        else:
            raise TypeError("Недопустимый тип данных: {}".format(self.type))

    def read(self, position=0):
        if position == 0:
            position = self.min
        if position < self.min or position > self.max:
            raise IndexError("Позиция вне диапазона допустимых значений")
        if self.max < 1:
            return self.parsed
        if self.type is dict:
            position = str(position)
            return self.parsed[position]
        elif self.type is list:
            return self.parsed[position]

    def reload(self):

        try:
            pass
        except:
            raise TypeError("Файл не соответствует формату json")
        self.type = type(self.parsed)

        if self.type is dict:
            self.min = int(min(self.parsed)) if len(self.parsed) else 0
            self.max = int(max(self.parsed)) if len(self.parsed) else 0
        elif self.type is list:
            self.min = 0
            self.max = len(self.parsed)
        else:
            raise TypeError("Недопустимый тип данных: {}".format(self.type))

    def write(self,data,position=None):
        if position is None:
            position = self.max+1
        if self.type is dict:
            position = str(position)
            self.parsed[position]=data
        elif self.type is list:
            self.parsed[position]=data
        self.max += 1
        self.file.seek(0)
        self.file.write(dumps(self.parsed))

