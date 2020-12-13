from shared_libs.dict_functions import Map


class Action:

    def __new__(cls, data):
        action = Map(data['action'])
        return structure[action.action_type](action)

    ws = None


class Connection:
    __slots__ = ('client', 'data')
    action_type = 'connect'

    def __init__(self, data):
        self.client = Map(data['client'])
        self.data = data


class LogRequest:
    __slots__ = ('data',)
    action_type = 'need_log'

    def __init__(self, data):
        self.data = data


class InitSimulator: # group
    __slots__ = ('data',)
    action_type = 'init_simulator'

    def __init__(self, data):
        self.data = data


class SimulatorControl:
    __slots__ = ('simulator_control', 'data')
    action_type = 'simulator_control'

    def __init__(self, data):
        self.simulator_control = Map(data[self.action_type])
        self.data = data


class ServiceControl:
    __slots__ = ('service_name', 'control_type', 'data')
    action_type = 'service_control'

    def __init__(self, data):
        service_control = Map(data['service_control'])
        self.service_name = service_control.service_name
        self.control_type = service_control.action_type
        self.data = data


class PluginInit:
    __slots__ = ('plugin_id', 'data')
    action_type = 'plugin_init'

    def __init__(self, data):
        self.plugin_id = data['plugin_id']
        self.data = data


class Plugins:  # group
    __slots__ = ('data',)
    action_type = 'plugins'

    def __init__(self, data):
        self.data = data

class Health:  # group
    __slots__ = ('data',)
    action_type = 'health'

    def __init__(self, data):
        self.data = data

class PluginCommand:
    __slots__ = ('data','plugin_id','command')
    action_type = 'plugin_command'

    def __init__(self, data):
        self.data = data
        self.plugin_id = data['plugin_id']
        self.command = data['command']



structure = {'action': Action, 'connect': Connection,
             'need_log': LogRequest,
             'init_simulator': InitSimulator,
             'simulator_control': SimulatorControl,
             'service_control': ServiceControl,
             'plugin_init': PluginInit,
             'plugins': Plugins,
             'health': Health,
             'plugin_command': PluginCommand}
