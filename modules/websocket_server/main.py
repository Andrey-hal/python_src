import asyncio
import json
import logging
import websockets
from modules.websocket_server.scheme import Action


class Client:
    def __init__(self, name='unknown',
                 client_type='default',
                 groups=None,
                 ws=None):
        if groups is None:
            groups = ['default', ]
        self.name = name
        self.type = client_type
        self.groups = groups
        self.ws = ws

    async def send(self, update):
        await self.ws.send(update)


log = logging.getLogger(name='service')

CLIENTS = set()
handlers = {}


def notify(target=None):
    if target is None:
        target = ['all']
    if hasattr(target, '__call__'):
        func = target

        async def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            li = []
            for user in CLIENTS:
                li.append({"user": user.ws, "event": result.create()})
            if CLIENTS:
                await asyncio.wait([l["user"].send(l["event"]) for l in li])

        return wrapper

    elif type(target) is list:
        def mm(func):
            async def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                li = []
                for user in CLIENTS:
                    if 'all' in target:
                        li.append({"user": user.ws, "event": result.create()})

                    elif any([g in target for g in user.groups]):
                        li.append({"user": user.ws, "event": result.create()})
                if CLIENTS:
                    await asyncio.wait([l["user"].send(l["event"]) for l in li])

            return wrapper

        return mm


def handler(action=None):
    if type(action) is str:
        action = Action.structure[action]

    def wrapper(func):
        if action.action_type not in handlers:
            handlers[action.action_type] = []
        handlers[action.action_type].append(func)

    return wrapper


@handler(action=Action.Connection)
async def register(action, websocket):
    client = Client(name=action.client.name,
                    client_type=action.client.client_type,
                    groups=action.client.groups,
                    ws=websocket)

    CLIENTS.add(client)
    for g in action.client.groups:
        if g in handlers:
            await asyncio.wait([h(action, client) for h in handlers[g]])
    return client


async def ws_worker(websocket, path):
    try:
        client = None
        async for message in websocket:

            try:
                data = json.loads(message)
            except:
                log.error("Ошибка парсинга JSON")
                continue

            if 'type' not in data:
                log.error("Ошибка парсинга JSON")
                continue

            if data['type'] not in Action.structure:
                log.error('Неизвестный тип события вебсокета')
                continue

            action = Action.structure[data['type']](data)

            # Регистрация клиентов
            if action.action_type == 'connect':
                result = await asyncio.gather(*[h(action, websocket) for h in handlers[action.action_type]])
                for i in result:
                    client = i
                if client is None:
                    log.error('Ошибка регистрации клиента')
                continue

            if action.action_type in handlers:
                await asyncio.wait([h(action, client) for h in handlers[action.action_type]])

    except websockets.exceptions.ConnectionClosedOK:
        CLIENTS.discard(websocket)
    except websockets.exceptions.ConnectionClosedError:
        CLIENTS.discard(websocket)
    finally:
        try:
            CLIENTS.discard(client)
        except:
            pass


try:
    start_server = websockets.serve(ws_worker, "0.0.0.0", 789)
except:
    log.error('Ошибка запуска WS сервера')

# asyncio.get_event_loop().run_until_complete(start_server)
# asyncio.get_event_loop().run_forever()
