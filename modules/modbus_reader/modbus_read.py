#!/usr/bin/env python
"""
Pymodbus Server With Custom Datablock Side Effect
--------------------------------------------------------------------------

This is an example of performing custom logic after a value has been
written to the datastore.
"""
# --------------------------------------------------------------------------- #
# import the modbus libraries we need
# --------------------------------------------------------------------------- #
from __future__ import print_function
from pymodbus.server.asynchronous import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSparseDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from threading import Thread
from models.work_db import *
from logs import logging
from modules.modbus_reader.configurator import bytes_unpack

log = logging.getLogger("modbus_reader")
log.propagate = False
source_name = "modbus_reader"

# --------------------------------------------------------------------------- #
# configure the service logging
# --------------------------------------------------------------------------- #
#
# import logging
# logging.basicConfig()
# log = logging.getLogger()
# log.setLevel(logging.DEBUG)

# --------------------------------------------------------------------------- #
# create your custom data block here
# --------------------------------------------------------------------------- #

class InputModbusDataBlock(ModbusSparseDataBlock):
    """ A datablock that stores the new value in memory
    and performs a custom action after it has been stored.
    """

    @db_session
    def write_to_base(self, read_structure):
        """
        Запись считанных из modbus данных
        :param read_structure: "Кадр" в формате (Имя из OPC, значение, ...)
        :return:
        """
        try:
            work_db.execute(
                """
                update variablework as v set flo = c.flo,tmstp = c.tmstp
                from (values {} ) as c(name, flo,tmstp)
                where c.name = v.name;
                """.format(
                    ",".join(
                        ["('{}',ARRAY[{}]::double precision[],CURRENT_TIMESTAMP)".format(i[0], i[1][1])
                         for i in read_structure.items()
                         if i[1][1] != "None"
                         ])))
            Health[source_name].tmstp = datetime.now()
        except Exception as e:
            # self.status = 'down'
            # self.stop_flag = True
            log.debug(format_exc())
            log.error('Ошибка записи в базу данных.')

    def setValues(self, address, value):
        """ Sets the requested values of the datastore

        :param address: The starting address
        :param value: The new values to be set
        """
        super(InputModbusDataBlock, self).setValues(address, value)

        # whatever you want to do with the written value is done here,
        # however make sure not to do too much work here or it will
        # block the server, espectially if the server is being written
        # to very quickly
        print("wrote {} to {}".format(value, address))
        read_structure = bytes_unpack(value, address)
        # frame = [(key, val[1]) for key, val in read_structure.items()]
        Thread(target=self.write_to_base, args=(read_structure,)).start()


def run_custom_db_server(ip='localhost', port=5020):
    # ----------------------------------------------------------------------- #
    # initialize your data store
    # ----------------------------------------------------------------------- #
    block = InputModbusDataBlock([0] * 100)
    store = ModbusSlaveContext(di=block, co=block, hr=block, ir=block)
    context = ModbusServerContext(slaves=store, single=True)

    # ----------------------------------------------------------------------- #
    # initialize the server information
    # ----------------------------------------------------------------------- #

    identity = ModbusDeviceIdentification()
    identity.VendorName = 'pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl = 'http://github.com/bashwork/pymodbus/'
    identity.ProductName = 'pymodbus Server'
    identity.ModelName = 'pymodbus Server'
    identity.MajorMinorRevision = '2.3.0'

    # ----------------------------------------------------------------------- #
    # run the server you want
    # ----------------------------------------------------------------------- #

    # p = Process(target=device_writer, args=(queue,))
    # p.start()
    # StartTcpServer(context, identity=identity, address=(ip, port))
    Thread(
        target=StartTcpServer,
        args=(context,),
        kwargs={'identity': identity, 'address': (ip, port)},
        daemon=True
    ).start()


if __name__ == "__main__":
    run_custom_db_server()
