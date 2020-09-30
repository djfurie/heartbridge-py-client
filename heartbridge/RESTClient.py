import datetime
import json
import logging
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class RESTClient:
    def __init__(self, url: str):
        self._base_url = url
        self._session = aiohttp.ClientSession()

    async def _post(self, endpoint: str, data: str):
        async with self._session.post(self._base_url + "/" + endpoint, data=data) as resp:
            return await resp.json()

    async def register(self, artist: str, title: str, performance_date: int = int(datetime.datetime.now().timestamp())):
        logger.info("Requesting token for time %d", performance_date)

        return await self._post("register", json.dumps({
            'action': 'register',
            'artist': artist,
            'title': title,
            'performance_date': performance_date}))

    async def update(self, token, updated_info):
        cmd_json = {
            'action': 'update',
            'token': token
        }
        merged_json = {**cmd_json, **updated_info}
        return await self._post("update", json.dumps(merged_json))

    async def close(self):
        await self._session.close()
