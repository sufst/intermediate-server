"""
    Southampton University Formula Student Team Intermediate Server
    Copyright (C) 2020 Nathan Rowley-Smith

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import asyncio
import json

import websockets

import common


class RestfulRequest:
    def __init__(self, websocket, request_str: str):
        self._request_str = request_str
        self._websocket = websocket

        self._dataset, self._filters, self._type = None, [], None

        self._logger = common.get_logger("Restful", "DEBUG")

        self._decode_request()

    def _decode_request(self):
        # Decode GET /sensors/RPM?timesince=<epoch>&amount=<n>
        try:
            split_space = self._request_str.split(" ")
            self._type = split_space[0]
            split_question = split_space[1].split("?")
            self._dataset = split_question[0]
            self._datasets = self._dataset.split("/")[1:]
            split_and = split_question[1].split("&")

            for fil in split_and:
                self._filters.extend([tuple(fil.split("="))])
        except Exception as error:
            self._logger.error(repr(error))
            self._websocket.send({"ERROR": [{"type": repr(error)}]})
            self._websocket.close()

    async def respond(self, response: dict):
        await self._websocket.send(json.dumps(response))
        await self._websocket.close()

    def get_type(self) -> str:
        return self._type

    def get_dataset(self) -> str:
        return self._dataset

    def get_datasets(self) -> list:
        return self._datasets

    def get_filters(self) -> list:
        return self._filters

    def __str__(self):
        return str({"type": self._type, "dataset": self._dataset, "filters": self._filters})


class Restful:
    def __init__(self, url: str, port: int):
        self._url, self._port = url, port
        self._server = websockets.serve(self._websocket_serve, self._url, self._port)
        self._request_callable = None

        self._logger = common.get_logger("Restful", "DEBUG")

    def serve(self, request_callable):
        self._request_callable = request_callable

        asyncio.get_event_loop().run_until_complete(self._server)
        self._logger.info(f"Serving on {self._url}:{self._port}")

    async def _websocket_serve(self, websocket, path: str):
        try:
            request = await websocket.recv()
            self._logger.info(f"Got request: {request}")

            request = RestfulRequest(websocket, request)

            await self._request_callable(request)
        except websockets.ConnectionClosedOK:
            pass
