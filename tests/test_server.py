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
import unittest
import socket
import struct
import time


class TestServer(unittest.TestCase):
    def test_client_socket(self):
        core_pdu_stream_core = struct.pack("<BBIdHHHHHHHH", 1, 0, 0xffff, time.time(), 1, 2, 3, 4, 5, 6, 7, 8)
        core_pdu_stream_core_2 = struct.pack("<BBIdHHHHHHHH", 1, 0, 0xffff, time.time()+2, 9, 10, 11, 12, 13, 14, 15, 16)
        core_pdu_stream_aero = struct.pack("<BBHdHHHHHHH", 1, 1, 0xff, time.time()+4, 1, 2, 3, 4, 5, 6, 7)
        core_pdu_stream_diag = struct.pack("<BBHdHHHH", 1, 2, 0xff, time.time()+6, 1, 0, 1, 1)
        core_pdu_stream_power = struct.pack("<BBHdHHHHH", 1, 3, 0xff, time.time()+8, 1, 2, 3, 4, 5)
        core_pdu_stream_sus = struct.pack("<BBHdHHHH", 1, 4, 0xff, time.time()+10, 1, 2, 3, 4)
        core_pdu_stream_misc = struct.pack("<BBHdHHHH", 1, 5, 0xff, time.time()+12, 1, 2, 3, 4)

        test_streams = [core_pdu_stream_core,
                        core_pdu_stream_core_2,
                        core_pdu_stream_aero + core_pdu_stream_diag,
                        core_pdu_stream_power + core_pdu_stream_sus + core_pdu_stream_misc]

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 19900))
            for stream in test_streams:
                sock.send(stream)
