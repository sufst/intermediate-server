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
