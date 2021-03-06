"""
    Southampton University Formula Student Team Intermediate Server
    Copyright (C) 2021 Nathan Rowley-Smith

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
import unittest

import websockets

import restful


async def _restful_serve(request: restful.RestfulRequest):
    print(request)

    if request.get_type() == "GET":
        if request.get_dataset() == "/sensors":
            for req_filter in request.get_filters():
                filter_name, filter_value = req_filter
                await request.respond({filter_name: int(filter_value)})


async def _test_connect():
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.close()


async def _test_request():
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.send("GET /sensors?amount=10")

        response_json = await websocket.recv()
        response = json.loads(response_json)

        print(response)

        if not response == {"amount": 10}:
            raise Exception

        await websocket.close()


class TestRestfulConnect(unittest.TestCase):
    def test_connect(self):
        # restful.Restful("localhost", 8765).serve(_restful_serve)
        asyncio.get_event_loop().run_until_complete(_test_connect())

    def test_request(self):
        asyncio.get_event_loop().run_until_complete(_test_request())


if __name__ == '__main__':
    unittest.main()
