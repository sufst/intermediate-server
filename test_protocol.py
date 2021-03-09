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
import protocol
import struct


def _serve_pdu_fields(fields: dict):
    print(fields)


class TestProtocol(unittest.TestCase):
    def test_initialise(self):
        proto = protocol.Protocol()

    def test_decode(self):
        proto = protocol.Protocol()

        core_pdu_stream_core = struct.pack("<BBHHHHHHHH", 1, 0, 1, 2, 3, 4, 5, 6, 7, 8)
        core_pdu_stream_core_2 = struct.pack("<BBHHHHHHHH", 1, 0, 9, 10, 11, 12, 13, 14, 15, 16)
        core_pdu_stream_aero = struct.pack("<BBHHHHHHH", 1, 1, 1, 2, 3, 4, 5, 6, 7)
        core_pdu_stream_diag = struct.pack("<BBHHHH", 1, 2, 1, 0, 1, 1)
        core_pdu_stream_power = struct.pack("<BBHHHHH", 1, 3, 1, 2, 3, 4, 5)
        core_pdu_stream_sus = struct.pack("<BBHHHH", 1, 4, 1, 2, 3, 4)
        core_pdu_stream_misc = struct.pack("<BBHHHH", 1, 5, 1, 2, 3, 4)

        test_streams = [core_pdu_stream_core,
                        core_pdu_stream_core_2,
                        core_pdu_stream_aero + core_pdu_stream_diag,
                        core_pdu_stream_power + core_pdu_stream_sus + core_pdu_stream_misc]

        for stream in test_streams:
            proto.decode_to(stream, _serve_pdu_fields)

    def test_decode_corrupt(self):
        proto = protocol.Protocol()

        core_pdu_stream = struct.pack("<BBHHHHHHHH", 1, 1, 1, 2, 3, 4, 5, 6, 7, 8)
        core_pdu_stream_2 = struct.pack("<BBHHHHHHHH", 5, 0, 9, 10, 11, 12, 13, 14, 15, 16)

        test_streams = [core_pdu_stream, core_pdu_stream_2, core_pdu_stream + core_pdu_stream_2]

        for stream in test_streams:
            self.assertRaises(Exception, proto.decode_to(stream, _serve_pdu_fields))
