from .data_format import *
from definitions import ROOT_DIR
class Simulator:
    def __init__(self,db=None,db_session=None):
        self.file = open(ROOT_DIR+'/modules/simulator/data.json', 'r+',encoding='utf-8')
        self.active = False
        self.play = False
        self.db = db
        self.db_session = db_session
        self.variables = {}
        self.min = 0
        self.max = 1
        self.type = Json_Type(self.file)
        self.position = 0
        self.load()

    def reload(self):
        self.file.seek(0)

    def load(self):
        self.variables = self.type.read()
        self.min = self.type.min
        self.max = self.type.max
        self.position = self.min
        return self.variables

    def seek(self,position):
        self.variables = self.type.read(position)
        self.position = position
        return self.variables

    def write_to_base(self, ):
        with self.db_session():
            self.db.execute(
                """
                update variablework as v set flo = c.flo,tmstp = c.tmstp
                from (values {} ) as c(name, flo,tmstp) 
                where c.name = v.name;
                """.format(
                    ",".join(
                        ["('{}',ARRAY[{}]::double precision[],CURRENT_TIMESTAMP)".format(k,v)
                         for k,v in self.variables.items() if k != ''
                         ])))

    def write_to_file(self,data):
        return self.type.write(data)