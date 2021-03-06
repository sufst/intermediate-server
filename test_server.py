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
import threading
import unittest

import websockets

import server


class ServerThread(threading.Thread):
    def __init__(self):
        """
        Initialise the thread to run the server on in the background for testing.
        """
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.running = False

    def run(self):
        """
        Thread run to run the server event loop.
        """
        self.running = True
        asyncio.set_event_loop(self.loop)
        server.Server("127.0.0.1", 19900, "COM0", 115200, "FFFFFFFFFFFFFFFF", "INFO").run()

    def stop(self):
        """
        Stop the threads event loop (will stop the server).
        """
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join()
        self.running = False


async def _test_request():
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.send("GET /sensors?amount=10")

        response_json = await websocket.recv()
        response = json.loads(response_json)

        print(response)

        await websocket.close()


class TestServerRestful(unittest.TestCase):
    def test_restful(self):
        ser_thread = ServerThread()
        ser_thread.start()

        asyncio.get_event_loop().run_until_complete(_test_request())
        ser_thread.stop()
