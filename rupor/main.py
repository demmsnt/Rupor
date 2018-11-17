from uuid import uuid4
import asyncio
import aiohttp
from aiohttp import web
import aioredis
from services import config, users


class RuporApp(web.Application):
    def __init__(self, config, users, *args, channel='channel', **kwargs):
        super().__init__(*args, **kwargs)
        self.sub_task_handle = None
        self.config = config
        self.channel_name = channel
        self.pub = None
        self.sub = None
        self.clients = {}
        self.add_routes([
            web.get('/ws', self.ws_handler),
            web.get('/status', self.status)])
        self.cleanup_ctx.append(self.pubsub_engine)

    async def status(self, request):
        return web.Response(text='Status page')

    async def pubsub_engine(self, app):
        print("Start pubsub_engine")
        loop = asyncio.get_event_loop()
        self.pub = await aioredis.create_redis(
            self.config['redis'],
            loop=loop)
        self.sub = await aioredis.create_redis(
            self.config['redis'],
            loop=loop)
        res = await self.sub.subscribe(self.channel_name)
        self.channel = res[0]
        self.sub_task_handle = asyncio.ensure_future(self.sub_task(self.channel))
        yield
        self.sub.unsubscribe(self.channel_name)
        self.pub.close()
        self.sub.close()
        print("Stop pubsub engine")
        await self.pub.wait_closed()
        await self.sub.wait_closed()

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        i_am = uuid4().hex
        self.clients[i_am] = ws
        try:
            await ws.prepare(request)
        except Exception as e:
            raise e
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    await ws.send_str(msg.data + '/answer')
                    if self.channel:
                        print("Send to channel")
                        try:
                            await self.pub.publish_json(self.channel_name, {'msg': msg.data})
                        except Exception as e:
                            print("Exception", e)
                            raise e
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                      ws.exception())
        return ws

    async def sub_task(self, ch):
        print("Start pubsub task")
        try:
            while await ch.wait_message():
                msg = await ch.get_json()
                print("msg=", msg)
                to_send = []
                for k, v in self.clients.items():
                    to_send.append((k, v))
                for k, v in to_send:
                    await v.send_str(str(msg) + 'from redis')
        except Exception as e:
            print("!!!", e)
            raise e

def main():
    app = RuporApp(config.config, users.UsersSvc())
    web.run_app(app)


if __name__ == '__main__':
    main()