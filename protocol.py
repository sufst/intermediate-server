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
from __future__ import annotations
from typing import Optional
import json
import struct

AIPDU, ACPDU, AAPDU, ADPDU, APPDU, ASPDU, AMPDU = list(range(1, 8))
CAR, CAR_EMULATOR, GUI = list(range(1, 4))
START_BYTE, FRAME_TYPE, SEQ_NUM, EPOCH, LENGTH = list(range(5))
CLIENT_TYPE, SW_VER, CLIENT_NAME = list(range(5, 8))
RPM, WATER_TEMP_C, TPS_PERC, BATTERY_MV, EXTERNAL_5V_MV, FUEL_FLOW, LAMBDA, SPEED_KPH = list(range(5, 13))


def get_frame_from_buffer(buffer: bytes) -> Optional[ProtocolAIPDU, ProtocolACPDU]:
    frame_type_class_dict = {AIPDU: ProtocolAIPDU, ACPDU: ProtocolACPDU}
    if len(buffer) > 12:
        header = ProtocolHeader()
        header.unpack_raw(buffer[:12])
        if header.start_byte == 1 and not header.length == 0 and header.frame_type in frame_type_class_dict:
            frame = frame_type_class_dict[header.frame_type]()
            frame.unpack_raw(buffer)
            return frame

    return None


class ProtocolBase:
    def __init__(self) -> None:
        pass

    def pack_raw(self) -> None:
        raise NotImplementedError

    def unpack_raw(self, buffer: bytes) -> None:
        raise NotImplementedError

    def pack_json(self) -> str:
        raise NotImplementedError

    def unpack_json(self, buffer: str) -> None:
        raise NotImplementedError

    def __str__(self) -> str:
        raise NotImplementedError

    def __eq__(self, other: ProtocolBase) -> bool:
        raise NotImplementedError


class ProtocolHeader(ProtocolBase):
    def __init__(self) -> None:
        """
        Initialise a protocol HEADER instance
        """
        super().__init__()

        self.start_byte = 1
        self.frame_type = 0
        self.seq_num = 0
        self.epoch = 0
        self.length = 0

    def pack_raw(self) -> bytes:
        """
        Pack self to little-endian bytes.
        """
        return struct.pack("<BBIIH", self.start_byte, self.frame_type, self.seq_num, self.epoch, self.length)

    def unpack_raw(self, buffer: bytes) -> None:
        """
        Unpack a buffer containing a little-endian header frame into self.
        :param buffer:  The buffer containing the header frame
        """
        self.start_byte, self.frame_type, self.seq_num, self.epoch, self.length = struct.unpack("<BBIIH", buffer)

    def pack_json(self) -> str:
        """
        Pack self to a JSON string.
        """
        return json.dumps({FRAME_TYPE: self.frame_type, SEQ_NUM: self.seq_num,
                           EPOCH: self.epoch})

    def unpack_json(self, buffer: str) -> None:
        """
        Unpack a JSON string into self.
        :param buffer:  The JSON string.
        """
        temp = json.loads(buffer)
        self.frame_type = temp[FRAME_TYPE]
        self.seq_num = temp[SEQ_NUM]
        self.epoch = temp[EPOCH]

    def __str__(self) -> str:
        """
        Get a string representation of self.
        """
        return str(
            {"FRAME_TYPE": self.frame_type, "SEQ_NUM": self.seq_num, "EPOCH": self.epoch, "LENGTH": self.length})

    def __eq__(self, other: ProtocolHeader) -> bool:
        return self.frame_type == other.frame_type and self.seq_num == other.seq_num and self.epoch == other.epoch and \
               self.length == other.length


class ProtocolAIPDU(ProtocolBase):
    def __init__(self) -> None:
        """
        Initialise a protocol AIPDU instance
        """
        super().__init__()

        self.header = ProtocolHeader()
        self.header.frame_type = AIPDU
        self.client_type = 0
        self.sw_ver = 0
        self.client_name = ""

    def pack_raw(self) -> bytes:
        """
        Pack self to little-endian bytes.
        """
        temp = struct.pack("<BI", self.client_type, self.sw_ver) + self.client_name.encode()
        self.header.length = len(temp)
        return self.header.pack_raw() + temp

    def unpack_raw(self, buffer: bytes) -> None:
        """
        Unpack a buffer containing a little-endian header frame into self.
        :param buffer:  The buffer containing the header frame
        """
        self.header.unpack_raw(buffer[:12])
        self.client_type, self.sw_ver = struct.unpack("<BI", buffer[12:17])
        self.client_name = buffer[17:].decode()

    def pack_json(self) -> str:
        """
        Pack self to a JSON string.
        """
        return self.header.pack_json() + json.dumps({CLIENT_TYPE: self.client_type, SW_VER: self.sw_ver,
                                                     CLIENT_NAME: self.client_name})

    def unpack_json(self, buffer: str) -> None:
        """
        Unpack a JSON string into self.
        :param buffer:  The JSON string.
        """
        temp = json.loads(buffer)
        self.header.frame_type = temp[FRAME_TYPE]
        self.header.seq_num = temp[SEQ_NUM]
        self.header.epoch = temp[EPOCH]
        self.client_type = temp[CLIENT_TYPE]
        self.sw_ver = temp[SW_VER]
        self.client_name = temp[CLIENT_NAME]

    def __str__(self) -> str:
        """
        Get a string  representation of self.
        """
        return str(self.header) + str({"CLIENT_TYPE": self.client_type, "SW_VER": self.sw_ver,
                                       "CLIENT_NAME": self.client_name})

    def __eq__(self, other: ProtocolAIPDU) -> bool:
        return self.header == other.header and self.client_type == other.client_type and \
               self.sw_ver == other.sw_ver and self.client_name == self.client_name


class ProtocolACPDU(ProtocolBase):
    def __init__(self) -> None:
        """
        Initialise a protocol ACPDU instance
        """
        super().__init__()

        self.header = ProtocolHeader()
        self.header.frame_type = ACPDU
        self.rpm = 0
        self.water_temp = 0
        self.tps_perc = 0
        self.battery_mv = 0
        self.external_5v_mv = 0
        self.fuel_flow = 0
        self.lambda_val = 0
        self.speed_kph = 0

    def pack_raw(self) -> bytes:
        """
        Pack self to little-endian bytes.
        """
        temp = struct.pack("<HhHHHHhh", self.rpm, self.water_temp, self.tps_perc, self.battery_mv, self.external_5v_mv,
                           self.fuel_flow, self.lambda_val, self.speed_kph)
        self.header.length = len(temp)
        return self.header.pack_raw() + temp

    def unpack_raw(self, buffer: bytes) -> None:
        """
        Unpack a buffer containing a little-endian header frame into self.
        :param buffer:  The buffer containing the header frame
        """
        self.header.unpack_raw(buffer[:12])
        self.rpm, self.water_temp, self.tps_perc, self.battery_mv, self.external_5v_mv, \
        self.fuel_flow, self.lambda_val, self.speed_kph = struct.unpack("<HhHHHHhh", buffer[12:])

    def pack_json(self) -> str:
        """
        Pack self to a JSON string.
        """
        return self.header.pack_json() + json.dumps({RPM: self.rpm, WATER_TEMP_C: self.water_temp,
                                                     TPS_PERC: self.tps_perc, BATTERY_MV: self.battery_mv,
                                                     EXTERNAL_5V_MV: self.external_5v_mv, FUEL_FLOW: self.fuel_flow,
                                                     LAMBDA: self.lambda_val, SPEED_KPH: self.speed_kph})

    def unpack_json(self, buffer: str) -> None:
        """
        Unpack a JSON string into self.
        :param buffer:  The JSON string.
        """
        temp = json.loads(buffer)
        self.header.frame_type = temp[FRAME_TYPE]
        self.header.seq_num = temp[SEQ_NUM]
        self.header.epoch = temp[EPOCH]
        self.rpm = temp[RPM]
        self.water_temp = temp[WATER_TEMP_C]
        self.tps_perc = temp[TPS_PERC]
        self.battery_mv = temp[BATTERY_MV]
        self.external_5v_mv = temp[EXTERNAL_5V_MV]
        self.fuel_flow = temp[FUEL_FLOW]
        self.lambda_val = temp[LAMBDA]
        self.speed_kph = temp[SPEED_KPH]

    def __str__(self) -> str:
        """
        Get a string  representation of self.
        """
        return str(self.header) + str({"RPM": self.rpm, "WATER_TEMP_C": self.water_temp,
                                       "TPS_PERC": self.tps_perc, "BATTERY_MV": self.battery_mv,
                                       "EXTERNAL_5V_MV": self.external_5v_mv, "FUEL_FLOW": self.fuel_flow,
                                       "LAMBDA": self.lambda_val, "SPEED_KPH": self.speed_kph})

    def __eq__(self, other: ProtocolACPDU) -> bool:
        return self.header == other.header and self.rpm == other.rpm and \
               self.water_temp == other.water_temp and self.tps_perc == self.tps_perc and \
               self.battery_mv == other.battery_mv and self.external_5v_mv == self.external_5v_mv and \
               self.fuel_flow == other.fuel_flow and self.lambda_val == self.lambda_val and \
               self.speed_kph == other.speed_kph
