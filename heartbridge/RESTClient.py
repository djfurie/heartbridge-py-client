import datetime
import json
import logging
import aiohttp
import asyncio
from typing import Union

logger = logging.getLogger(__name__)


class RESTClient:
    def __init__(self, url: str):
        self._base_url = url
        self._session = aiohttp.ClientSession()

    async def _post(self, endpoint: str, data: str):
        async with self._session.post(self._base_url + "/" + endpoint,
                                      data=data) as resp:
            return await resp.json()

    async def _get(self, endpoint: str):
        async with self._session.get(self._base_url + "/" + endpoint) as resp:
            return await resp.json()

    async def register(self, artist: str, title: str, email: str, description: str,
                       duration: int,
                       performance_date: Union[int, str] = -1):

        if type(performance_date) is int:
            if performance_date < 0:
                performance_date = int(datetime.datetime.now().timestamp())
            logger.info("Requesting token for time %d", performance_date)
        else:
            logger.info("Requesting token for time %s", performance_date)

        return await self._post("register", json.dumps({
            'action': 'register',
            'artist': artist,
            'title': title,
            'performance_date': performance_date,
            'description': description,
            'email': email,
            'duration': duration
        }))

    async def update(self, token, updated_info):
        cmd_json = {
            'action': 'update',
            'token': token
        }
        merged_json = {**cmd_json, **updated_info}
        return await self._post("update", json.dumps(merged_json))

    async def get_event_details(self, performance_id: str):
        return await self._get(f"events/{performance_id}")

    async def get_events(self):
        return await self._get("events/")

    async def get_event_status(self, performance_id: str):
        return await self._get(f"events/{performance_id}/status")

    async def set_event_status(self, performance_id: str, token: str, status: str):
        return await self._post(f"events/{performance_id}/status",
                                json.dumps({"token": token, "status": status}))

    async def delete_performance(self, token: str):
        return await self._post("delete", json.dumps({
            'token': token
        }))

    async def close(self):
        await self._session.close()
