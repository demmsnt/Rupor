"""Simple web chat for site

В nginx конфиг выглядит так

location /socket.io/ {
            proxy_pass http://localhost:8080;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
    }

"""
import logging
import datetime
from uuid import uuid4
import asyncio
import aiohttp
from aiohttp import web
import aioredis
import socketio
from services import config, users

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


class RuporApp(web.Application):
    """Base class for rupor"""
    def __init__(self, config, users, *args, history_length=10, debug=False, **kwargs):
        """Initialisation.

        config - is a configuration object
        users - is a users object for detect user
        history_length - длина истории которую передать новому клиенту
        debug - если истина выставить еще статистику....
        """
        super().__init__(*args, **kwargs)
        self.history_length = history_length
        self.history = []
        self.users = users
        self.sub_task_handle = None
        self.config = config
        self.pub = None
        self.sub = None
        self.clients = {}
        #routes = [web.get('/ws', self.ws_handler)]
        routes = []
        self.sio = socketio.AsyncServer()
        self.sio.attach(self)
        self.sio.on('connect', handler=self.on_connect)
        self.sio.on('message', handler=self.on_message)
        self.sio.on('disconnect', handler=self.on_disconnect)
        if debug:
            routes.append(web.get('/status', self.status))
        self.add_routes(routes)
        self.cleanup_ctx.append(self.pubsub_engine)
        self.in_shutdown = False

    async def status(self, request):
        return web.Response(text='Status page')

    async def pubsub_engine(self, app):
        """Aiohttp context.

        Он при старте приложения запустится,
        сделает yield, а при остановке запустится снова.

        """
        logger.info("Start pubsub_engine")
        loop = asyncio.get_event_loop()
        self.pub = await aioredis.create_redis(
            self.config['redis']['url'],
            loop=loop)
        self.sub = await aioredis.create_redis(
            self.config['redis']['url'],
            loop=loop)
        res = await self.sub.subscribe(self.config['redis']['channel'])
        self.channel = res[0]
        self.sub_task_handle = asyncio.ensure_future(self.sub_task(self.channel))
        yield
        self.in_shutdown = True
        # Остановим через редис
        await self.pub.publish_json(self.config['redis']['channel'], {'msg': 'stop'})
        self.sub.unsubscribe(self.config['redis']['channel'])
        self.pub.close()
        self.sub.close()
        logger.info("Stop pubsub engine")
        await self.pub.wait_closed()
        await self.sub.wait_closed()

    async def on_connect(self, sid, env):
        request = env['aiohttp.request']
        user = self.users.get_user(request)
        self.clients[sid] = user
        logger.info('Connected sid:{}, user:{}'.format(sid, str(user)))
        await self.sio.emit('message', data={'t': 'history', 'd': self.history}, room=sid)
        await self.pub.publish_json(self.config['redis']['channel'], {'t': 'info', 'data': 'User {} joined'.format(str(user))})

    async def on_message(self, sid, data):
        print("Message", sid, data)
        if data.get('t') == 'msg':
            user = self.clients.get(sid)
            data['user'] = user
            await self.pub.publish_json(self.config['redis']['channel'], data)

    def on_disconnect(self, sid):
        user = self.clients.get(sid)
        if sid in self.clients:
            del(self.clients[sid])
        logger.info("Disconnected sid:{}, user:{}".format(sid, str(user)))

    # async def ws_handler(self, request):
    #     """Вебсокет хандлер"""
    #     ws = web.WebSocketResponse()
    #     i_am = uuid4().hex
    #     user = self.users.get_user(request)
    #     logger.info('{} Enter'.format(i_am))
    #     self.clients[i_am] = ws
    #     try:
    #         await ws.prepare(request)
    #     except Exception as e:
    #         raise e
    #     await ws.send_json(self.history)
    #     async for msg in ws:
    #         if msg.type == aiohttp.WSMsgType.TEXT:
    #             if self.channel:
    #                 send_msg = {
    #                     'id': uuid4().hex,
    #                     't': datetime.datetime.utcnow().isoformat(),
    #                     'm': msg.data,
    #                     'u': user
    #                 }
    #                 await self.pub.publish_json(self.config['redis']['channel'], send_msg)
    #         elif msg.type == aiohttp.WSMsgType.ERROR:
    #             logger.error('ws connection closed with exception %s' % ws.exception())
    #     logger.info('{} Exit'.format(i_am))
    #     del(self.clients[i_am])
    #     return ws

    async def log_message(self, msg):
        """Простой логгер - если надо будет в БД будем писать в БД"""
        logger.info("msg={}".format(str(msg)))

    async def sub_task(self, ch):
        try:
            logger.info("Start pubsub task")
            while await ch.wait_message():
                if self.in_shutdown:
                    break
                msg = await ch.get_json()
                await self.log_message(msg)
                to_send = []
                for k, v in self.clients.items():
                    to_send.append((k, v))
                for k, v in to_send:
                    if msg.get('t') == 'msg':
                        self.history.append(msg)
                        self.history = self.history[-1 * self.history_length:]
                    await self.sio.emit('message', data=msg, room=k)
        except Exception as e:
            print("E", e)
            raise e


def main():
    app = RuporApp(config.config, users.UsersSvc())
    web.run_app(app)


if __name__ == '__main__':
    main()