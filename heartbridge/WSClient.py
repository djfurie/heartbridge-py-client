import datetime
import json
import logging
import websockets

logger = logging.getLogger(__name__)


class WSClient:
    def __init__(self, url):
        self._websocket_url = url
        self._ws: websockets.WebSocketClientProtocol = None

    @property
    def is_connected(self):
        if not self._ws:
            return False
        return self._ws.state == websockets.protocol.State.OPEN

    @property
    def connection_id(self):
        return self._ws.request_headers['Sec-WebSocket-Key']

    async def connect(self, url=None):
        if url:
            self._websocket_url = url
        self._ws = await websockets.connect(self._websocket_url)

    async def close(self):
        await self._ws.close()

    async def subscribe(self, performance_id):
        logger.info("Subscribing to Performance ID: %s", performance_id)
        await self._ws.send(json.dumps({'action': 'subscribe',
                                        'performance_id': performance_id}))

    async def register(self, artist: str, title: str, performance_date: int = int(datetime.datetime.now().timestamp())):
        logger.info("Requesting token for time %d", performance_date)

        await self._ws.send(json.dumps({
            'action': 'register',
            'artist': artist,
            'title': title,
            'performance_date': performance_date}))

        return await self._ws.recv()

    async def update(self, token, updated_info):
        cmd_json = {
            'action': 'update',
            'token': token
        }

        await self._ws.send(json.dumps({**cmd_json, **updated_info}))
        return await self._ws.recv()

    async def publish(self, token, heartrate):
        cmd_json = {
            'action': 'publish',
            'heartrate': heartrate,
            'token': token
        }

        await self._ws.send(json.dumps(cmd_json))

    async def wait_for_data(self):
        return await self._ws.recv()

    def peek_rx(self):
        return len(self._ws.frame_buffer.recv_buffer)
