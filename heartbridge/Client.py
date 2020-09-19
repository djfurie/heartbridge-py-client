import datetime
import json
import logging
import websocket

logger = logging.getLogger(__name__)


class Client:
    def __init__(self, url):
        self._websocket_url = url
        self._ws = websocket.create_connection(url, timeout=5, enable_multithread=True)

    @property
    def is_connected(self):
        return self._ws.connected

    @property
    def connection_id(self):
        return self._ws.headers['sec-websocket-accept']

    def close(self):
        self._ws.close()

    def subscribe(self, performance_id):
        logger.info("Subscribing to Performance ID: %s", performance_id)
        self._ws.send(json.dumps({'action': 'subscribe',
                                  'performance_id': performance_id}))

    def register(self, artist: str, title: str, performance_date: int = int(datetime.datetime.now().timestamp())):
        logger.info("Requesting token for time %d", performance_date)

        self._ws.send(json.dumps({
            'action': 'register',
            'artist': artist,
            'title': title,
            'performance_date': performance_date}))

        return self._ws.recv()

    def update(self, token, updated_info):
        cmd_json = {
            'action': 'update',
            'token': token
        }

        self._ws.send(json.dumps({**cmd_json, **updated_info}))
        return self._ws.recv()

    def publish(self, token, heartrate):
        cmd_json = {
            'action': 'publish',
            'heartrate': heartrate,
            'token': token
        }

        self._ws.send(json.dumps(cmd_json))
        return self._ws.recv()

    def wait_for_data(self):
        return self._ws.recv()

    def peek_rx(self):
        return len(self._ws.frame_buffer.recv_buffer)
