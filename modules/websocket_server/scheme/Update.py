from json import dumps
class up:
    def create(self):
        t = {s: getattr(self, s) for s in self.slots__ if hasattr(self, s)}
        t.update({'update_type': self.update_type})
        return t


class Updates:

    def __init__(self):
        self.updates = []
    def __iadd__(self, other):
        self.updates.append(other.create())
        return self

    def add(self, *other):
        for i in other:
            self.updates.append(i.create())

    def create(self):
        a = {'type': 'updates', 'updates': self.updates}
        a = dumps(a)
        return a


class Health(up):
    slots__ = ['service_name', 'health', 'error_count', 'data', 'last_event_date']
    update_type = 'health'

    def __init__(self, service_name: str, health='unknown', error_count=0, data='', last_event_date=''):
        self.service_name = service_name
        self.health = health
        self.error_count = error_count
        self.data = data
        self.last_event_date = last_event_date


class Uptime(up):
    slots__ = ['time', ]
    update_type = 'uptime'

    def __init__(self, time=''):
        self.time = time


class Log(up):
    slots__ = ['log', ]
    update_type = 'log'

    def __init__(self, logs):
        self.log = [{
            "date": log_item["date"],
            "program": log_item["module"],
            "status": log_item["lvl"],
            "description": log_item["data"],
        } for log_item in logs]


class Simulator(up):
    slots__ = ["min", "max", "position", "active", "play", "variables"]
    update_type = 'simulator'

    def __init__(self, min, max, position, active, play, variables):
        self.min = min
        self.max = max
        self.position = position
        self.active = active
        self.play = play
        self.variables = variables


class Widget(up):
    slots__ = ['widget_type', 'widget_id', 'widget_style']
    update_type = 'update_widget'

    def __init__(self, update_type, widget_type, widget_id, widget_style):
        self.update_type = update_type
        self.widget_type = widget_type
        self.widget_id = widget_id
        self.widget_style = widget_style

    def add_type(self, type):
        setattr(self, type, None)
        self.slots__.append(type)


class PluginsInit(up):
    slots__ = ['plugins', ]
    update_type = 'plugins_init'

    def __init__(self, plugins):
        self.plugins = plugins


class CommandAnswer(up):
    slots__ = ['plugin_id', 'command']
    update_type = 'plugin_command_answer'

    def __init__(self, command, plugin_id=None):
        self.command = command
        self.plugin_id = plugin_id
