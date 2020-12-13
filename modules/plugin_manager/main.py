import logging
from traceback import format_exc
from modules.websocket_server import handler, notify
from modules.websocket_server.scheme import Action
from modules.websocket_server.scheme import Update
from json import dumps
import asyncio

log = logging.getLogger('plugins')
plugins = {}
inputs = {}
loop = asyncio.get_event_loop()

@notify(target=['plugins'])
def make_update(client, *updates):
    u = Update.Updates()
    u.add(*updates)
    return u

async def wait_input(inp):
    inputs[inp] = {'lock':asyncio.Event()}
    await inputs[inp]['lock'].wait()
    text = inputs[inp]['text']
    del inputs[inp]
    return text

def plugins_init(init):
    def wrapper(self):

        try:
            init(self)
        except:
            log.critical('Ошибка в плагине {}\n{}'.format(self.name, format_exc()))
        plugins[self.id] = self

    return wrapper


@handler(action='plugins')
async def return_plugins_list(action, client):
    u = Update.Updates()
    u.add(Update.PluginsInit([p.create_repr() for n, p in plugins.items()]))
    await client.send(u.create())


@handler(action=Action.PluginInit)
async def plugin_init(action, client):
    if action.plugin_id not in plugins:
        return
    plugin = plugins[action.plugin_id]
    plugin.client = client
    await plugin.create_widgets()


@handler(action=Action.PluginCommand)
async def command(action, client):
    plugin = plugins[action.plugin_id]
    wat = plugin.handle_command(action.command)
    if wat is not None:
        tasks = [loop.create_task(f(*wat[1])) for f in wat[0]]
    elif action.command.split(' ')[0] in inputs:
        inputs[action.command.split(' ')[0]].update(text=action.command)
        inputs[action.command.split(' ')[0]]['lock'].set()

class Manager:
    def __init__(self):
        self.plugins = {}


from plugins import *
