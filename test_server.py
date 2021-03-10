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
import socket
import struct
import websockets
import time
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
        server.Server().serve_forever()

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

    def test_client_socket(self):
        ser_thread = ServerThread()
        ser_thread.start()

        core_pdu_stream_core = struct.pack("<BBHdHHHHHHHH", 1, 0, 0x05, time.time(), 1, 2, 3, 4, 5, 6, 7, 8)
        core_pdu_stream_core_2 = struct.pack("<BBHdHHHHHHHH", 1, 0, 0x05, time.time()+2, 9, 10, 11, 12, 13, 14, 15, 16)
        core_pdu_stream_aero = struct.pack("<BBHdHHHHHHH", 1, 1, 0x05, time.time()+4, 1, 2, 3, 4, 5, 6, 7)
        core_pdu_stream_diag = struct.pack("<BBHdHHHH", 1, 2, 0x05, time.time()+6, 1, 0, 1, 1)
        core_pdu_stream_power = struct.pack("<BBHdHHHHH", 1, 3, 0x05, time.time()+8, 1, 2, 3, 4, 5)
        core_pdu_stream_sus = struct.pack("<BBHdHHHH", 1, 4, 0x05, time.time()+10, 1, 2, 3, 4)
        core_pdu_stream_misc = struct.pack("<BBHdHHHH", 1, 5, 0x05, time.time()+12, 1, 2, 3, 4)

        test_streams = [core_pdu_stream_core,
                        core_pdu_stream_core_2,
                        core_pdu_stream_aero + core_pdu_stream_diag,
                        core_pdu_stream_power + core_pdu_stream_sus + core_pdu_stream_misc]

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("127.0.0.1", 19900))
            for stream in test_streams:
                sock.send(stream)

        asyncio.get_event_loop().run_until_complete(_test_request())
        ser_thread.stop()
