from models.work_db import *
from models.local_db import *

@db_session
def clear():
    if input('Подвтердите(Y\\N):') in 'yYдДДада':
        delete(t for t in VariableWork)
        delete(t for t in Variable)
        delete(t for t in Table)
        delete(t for t in Variable)

if __name__ == "__main__":
    clear()