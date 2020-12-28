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
from typing import Callable
from typing import Dict
import json
import struct
import common
import protocol_factory
import asyncio
import datetime

AIPDU, ACPDU, AAPDU, ADPDU, APPDU, ASPDU, AMPDU = list(range(1, 8))
CAR, CAR_EMULATOR, GUI = list(range(1, 4))
START_BYTE, FRAME_TYPE, SEQ_NUM, EPOCH, LENGTH = list(range(5))
CLIENT_TYPE, SW_VER, CLIENT_NAME = list(range(5, 8))
RPM, WATER_TEMP_C, TPS_PERC, BATTERY_MV, EXTERNAL_5V_MV, FUEL_FLOW, LAMBDA, SPEED_KPH = list(range(5, 13))
EVO_SCANNER1, EVO_SCANNER2, EVO_SCANNER3, EVO_SCANNER4, EVO_SCANNER5, EVO_SCANNER6, EVO_SCANNER7 = list(range(5, 12))
ECU_STATUS_DISCONNECTED, ECU_STATUS_CONNECTED = list(range(2))
ENGINE_STATUS_OFF, ENGINE_STATUS_IDLE, ENGINE_STATUS_ACTIVE = list(range(3))
BATTERY_STATUS_DISCONNECTED, BATTERY_STATUS_LOW, BATTERY_STATUS_HEALTHY = list(range(3))
CAR_LOGGING_STATUS_OFF, CAR_LOGGING_STATUS_RUNNING = list(range(2))
ECU_STATUS, ENGINE_STATUS, BATTERY_STATUS, CAR_LOGGING_STATUS = list(range(5, 9))
INJECTION_TIME, INJECTION_DUTY_CYCLE, LAMBDA_PID_ADJUST, LAMBDA_PID_TARGET, ADVANCE = list(range(5, 10))
RIDE_HEIGHT_FL_CM, RIDE_HEIGHT_FR_CM, RIDE_HEIGHT_FLW_CM, RIDE_HEIGHT_REAR_CM = list(range(5, 9))
LAP_TIMER_S, ACCEL_FL_X_MG, ACCEL_FL_Y_MG, ACCEL_FL_Z_MG = list(range(5, 9))


class ProtocolCallbacks:
    def on_connection(self, protocol_client: ProtocolClient) -> None:
        raise NotImplementedError

    def on_lost(self, protocol_client: ProtocolClient, exc: Optional[Exception]) -> None:
        raise NotImplementedError

    def on_aipdu(self, protocol_client: ProtocolClient, header: ProtocolHeader, client_type: int, sw_ver: int,
                 client_name: str) -> None:
        raise NotImplementedError

    def on_acpdu(self, protocol_client: ProtocolClient, header: ProtocolHeader, rpm: int, water_temp_c: int,
                 tps_perc: int, battery_mv: int, external_5v_mv: int, fuel_flow: int, lambda_value: int,
                 speed_kph: int) -> None:
        raise NotImplementedError

    def on_aapdu(self, protocol_client: ProtocolClient, header: ProtocolHeader, evo_scanner1: int, evo_scanner2: int,
                 evo_scanner3: int, evo_scanner4: int, evo_scanner5: int, evo_scanner6: int, evo_scanner7: int) -> None:
        raise NotImplementedError

    def on_adpdu(self, protocol_client: ProtocolClient, header: ProtocolHeader, ecu_status: int, engine_status: int,
                 battery_status: int, car_logging_status: int) -> None:
        raise NotImplementedError

    def on_appdu(self, protocol_client: ProtocolClient, header: ProtocolHeader, injection_time: int,
                 injection_duty_cycle: int, lambda_pid_adjust: int, lambda_pid_target: int, advance: int) -> None:
        raise NotImplementedError

    def on_aspdu(self, protocol_client: ProtocolClient, header: ProtocolHeader, ride_height_fl_cm: int,
                 ride_height_fr_cm: int, ride_height_flw_cm: int, ride_height_rear_cm: int) -> None:
        raise NotImplementedError

    def on_ampdu(self, protocol_client: ProtocolClient, header: ProtocolHeader, lap_timer_s: int, accel_fl_x_mg: int,
                 accel_fl_y_mg: int, accel_fl_z_mg: int) -> None:
        raise NotImplementedError


class ProtocolClient:
    def __init__(self, callbacks: ProtocolCallbacks, client_type: int, client_name: str,
                 sw_ver: int, event_loop: asyncio.AbstractEventLoop, ip: str = "", port: int = 0, com: str = "",
                 baud: int = 0, mac: str = "", factory: protocol_factory.ProtocolFactoryBase = None,
                 verbose: str = "WARN") -> None:
        self._logger = common.get_logger(type(self).__name__, verbose)
        self._ip = ip
        self._port = port
        self._com = com
        self._baud = baud
        self._peer_mac = mac
        self._client_type = client_type
        self._client_name = client_name
        self._sw_ver = sw_ver
        self._event_loop = event_loop
        self._verbose = verbose
        self._callbacks = callbacks
        self._factory_callbacks = protocol_factory.ProtocolFactoryCallbacks()
        self._factory_callbacks.on_connection = self._on_connection
        self._factory_callbacks.on_receive = self._on_receive
        self._factory_callbacks.on_lost = self._on_connection_lost
        self._frame_type_dict = {AIPDU: ProtocolAIPDU, ACPDU: ProtocolACPDU, AAPDU: ProtocolAAPDU, ADPDU: ProtocolADPDU,
                                 APPDU: ProtocolAPPDU, ASPDU: ProtocolASPDU, AMPDU: ProtocolAMPDU}
        self._on_methods = {AIPDU: self._on_aipdu, ACPDU: self._on_acpdu, AAPDU: self._on_aapdu, ADPDU: self._on_adpdu,
                            APPDU: self._on_appdu, ASPDU: self._on_aspdu, AMPDU: self._on_aspdu}
        self._seq_num = 1
        self._on_con_lost = None
        self._factory = factory
        if self._client_type == CAR_EMULATOR:
            self._get_frame = self._get_frame_from_raw
        else:
            self._get_frame = self._get_frame_from_json

    def run(self) -> None:
        """
        Starts the protocol client event loop.
        """
        asyncio.run_coroutine_threadsafe(self._run(), self._event_loop)

    def _write_pdu(self, pdu: ProtocolBase) -> None:
        """
        Write a PDU to the under laying factory in the peers format.
        :param pdu: The PDU to write.
        """
        if self._client_type == CAR or self._client_type == CAR_EMULATOR:
            out = pdu.pack_raw()
        else:
            out = pdu.pack_json()

        self._logger.info(f"<- {out}")
        self._factory.write(out)

    def write_acpdu(self, rpm: int, water_temp_c: int, tps_perc: int, battery_mv: int, external_5v_mv: int,
                    fuel_flow: int, lambda_value: int, speed_kph: int) -> None:
        """
        Write a ACPDU to the peer.
        """
        pdu = ProtocolACPDU()
        pdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        pdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        pdu.rpm = rpm
        pdu.water_temp = water_temp_c
        pdu.tps_perc = tps_perc
        pdu.battery_mv = battery_mv
        pdu.external_5v_mv = external_5v_mv
        pdu.fuel_flow = fuel_flow
        pdu.lambda_val = lambda_value
        pdu.speed_kph = speed_kph

        self._logger.info(f"Created {pdu}")
        self._write_pdu(pdu)

    def write_aapdu(self, evo_scanner1: int, evo_scanner2: int, evo_scanner3: int, evo_scanner4: int, evo_scanner5: int,
                    evo_scanner6: int, evo_scanner7: int) -> None:
        """
        Write a AAPDU to the peer.
        """
        pdu = ProtocolAAPDU()
        pdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        pdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        pdu.evo_scanner1 = evo_scanner1
        pdu.evo_scanner2 = evo_scanner2
        pdu.evo_scanner3 = evo_scanner3
        pdu.evo_scanner4 = evo_scanner4
        pdu.evo_scanner5 = evo_scanner5
        pdu.evo_scanner6 = evo_scanner6
        pdu.evo_scanner7 = evo_scanner7

        self._logger.info(f"Created {pdu}")
        self._write_pdu(pdu)

    def write_adpdu(self, ecu_status: int, engine_status: int, battery_status: int, car_logging_status: int) -> None:
        """
        Write a ADPDU to the peer.
        """
        pdu = ProtocolADPDU()
        pdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        pdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        pdu.ecu_status = ecu_status
        pdu.engine_status = engine_status
        pdu.battery_status = battery_status
        pdu.car_logging_status = car_logging_status

        self._logger.info(f"Created {pdu}")
        self._write_pdu(pdu)

    def write_appdu(self, injection_time: int, injection_duty_cycle: int, lambda_pid_adjust: int,
                    lambda_pid_target: int, advance: int) -> None:
        """
        Write a APPDU to the peer.
        """
        pdu = ProtocolAPPDU()
        pdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        pdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        pdu.injection_time = injection_time
        pdu.injection_duty_cycle = injection_duty_cycle
        pdu.lambda_pid_adjust = lambda_pid_adjust
        pdu.lambda_pid_target = lambda_pid_target
        pdu.advance = advance

        self._logger.info(f"Created {pdu}")
        self._write_pdu(pdu)

    def write_aspdu(self, ride_height_fl_cm: int, ride_height_fr_cm: int, ride_height_flw_cm: int,
                    ride_height_rear_cm: int) -> None:
        """
        Write a ASPDU to the peer.
        """
        pdu = ProtocolASPDU()
        pdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        pdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        pdu.ride_height_fl_cm = ride_height_fl_cm
        pdu.ride_height_fr_cm = ride_height_fr_cm
        pdu.ride_height_flw_cm = ride_height_flw_cm
        pdu.ride_height_rear_cm = ride_height_rear_cm

        self._logger.info(f"Created {pdu}")
        self._write_pdu(pdu)

    def write_ampdu(self, lap_timer_s: int, accel_fl_x_mg: int, accel_fl_y_mg: int, accel_fl_z_mg: int) -> None:
        """
        Write a AMPDU to the peer.
        """
        pdu = ProtocolAMPDU()
        pdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        pdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        pdu.lap_timer_s = lap_timer_s
        pdu.accel_fl_x_mg = accel_fl_x_mg
        pdu.accel_fl_y_mg = accel_fl_y_mg
        pdu.accel_fl_z_mg = accel_fl_z_mg

        self._logger.info(f"Created {pdu}")
        self._write_pdu(pdu)

    async def _run(self) -> asyncio.coroutine:
        """
        The protocol client main event loop.
        """
        self._logger.info(f"Creating Protocol client {self._ip}:{self._port}")
        self._on_con_lost = self._event_loop.create_future()

        if self._factory is None:
            if self._client_type == CAR_EMULATOR or self._client_type == GUI:
                _, self._factory = await protocol_factory.create_client(self._ip, self._port, self._factory_callbacks,
                                                                     self._verbose, self._event_loop)

        self._logger.info("Protocol client Created")

        try:
            await self._on_con_lost
        finally:
            pass

        self._logger.warning("Stopped")

    def _get_frame_from_raw(self, buffer: bytes) -> Optional[ProtocolAIPDU, ProtocolACPDU, ProtocolAAPDU, ProtocolADPDU,
                                                             ProtocolAPPDU, ProtocolASPDU, ProtocolAMPDU]:
        """
        Get a frame from a raw buffer (from car stream)
        :param buffer: The raw buffer.
        """
        if len(buffer) > 12:
            header = ProtocolHeader()
            header.unpack_raw(buffer[:12])
            if header.start_byte == 1 and not header.length == 0 and header.frame_type in self._frame_type_dict:
                frame = self._frame_type_dict[header.frame_type]()
                frame.unpack_raw(buffer)
                return frame

        return None

    def _get_frame_from_json(self, buffer: bytes) -> Optional[ProtocolAIPDU, ProtocolACPDU, ProtocolAAPDU,
                                                              ProtocolADPDU, ProtocolAPPDU, ProtocolASPDU,
                                                              ProtocolAMPDU]:
        """
        Get a frame from a JSON buffer (from intermediate server)
        :param buffer: The JSON buffer.
        """
        raise NotImplementedError

    def _on_connection(self, factory: protocol_factory.ProtocolFactoryBase) -> asyncio.coroutine:
        """
        Invoked once the protocol factory has made a connection.
        A AIPDU frame is automatically sent upon connection made.
        :param factory: The factory that made a connection.
        """
        self._factory = factory
        self._callbacks.on_connection(self)
        pdu = ProtocolAIPDU()
        pdu.header.seq_num = self._seq_num
        self._seq_num += 1
        pdu.header.epoch = datetime.datetime.now().today().second
        pdu.client_type = self._client_type
        pdu.sw_ver = self._sw_ver
        pdu.client_name = self._client_name

        self._factory.write(pdu.pack_raw())

    def _on_receive(self, data: bytes) -> asyncio.coroutine:
        """
        Invoked once the protocol factory has received new data.
        :param data:    The received data.
        """
        self._logger.info(f"Handling {data}")

        pdu = self._get_frame(data)
        if pdu is not None:
            self._logger.info(str(pdu))
            if pdu.header.frame_type in self._on_methods:
                return self._on_methods[pdu.header.frame_type](pdu)
        else:
            self._logger.error("Failed to decode frame from buffer")

    def _on_connection_lost(self, exc: Optional[Exception]) \
            -> asyncio.coroutine:
        """
        Invoked once the protocol factory has lost connection.
        """
        self._logger.info("Lost connection to peer...")
        self._callbacks.on_lost(self, exc)

    def _on_aipdu(self, pdu: ProtocolAIPDU) -> None:
        self._logger.info("Handling AIPDU frame")
        self._callbacks.on_aipdu(self, pdu.header, pdu.client_type, pdu.sw_ver, pdu.client_name)

    def _on_acpdu(self, pdu: ProtocolACPDU) -> None:
        self._logger.info("Handling ACPDU frame")
        self._callbacks.on_acpdu(self, pdu.header, pdu.rpm, pdu.water_temp, pdu.tps_perc, pdu.battery_mv,
                                 pdu.external_5v_mv, pdu.fuel_flow, pdu.lambda_val, pdu.speed_kph)

    def _on_aapdu(self, pdu: ProtocolAAPDU) -> None:
        self._logger.info("Handling AAPDU frame")
        self._callbacks.on_aapdu(self, pdu.header, pdu.evo_scanner1, pdu.evo_scanner2, pdu.evo_scanner3,
                                 pdu.evo_scanner4, pdu.evo_scanner5, pdu.evo_scanner6, pdu.evo_scanner7)

    def _on_adpdu(self, pdu: ProtocolADPDU) -> None:
        self._logger.info("Handling ADPDU frame")
        self._callbacks.on_adpdu(self, pdu.header, pdu.ecu_status, pdu.engine_status, pdu.battery_status,
                                 pdu.car_logging_status)

    def _on_appdu(self, pdu: ProtocolAPPDU) -> None:
        self._logger.info("Handling APPDU frame")
        self._callbacks.on_appdu(self, pdu.header, pdu.injection_time, pdu.injection_duty_cycle, pdu.lambda_pid_adjust,
                                 pdu.lambda_pid_target, pdu.advance)

    def _on_aspdu(self, pdu: ProtocolASPDU) -> None:
        self._logger.info("Handling ASPDU frame")
        self._callbacks.on_aspdu(self, pdu.header, pdu.ride_height_fl_cm, pdu.ride_height_fr_cm, pdu.ride_height_flw_cm,
                                 pdu.ride_height_rear_cm)

    def _on_ampdu(self, pdu: AMPDU) -> None:
        self._logger.info("Handling AMPDU frame")
        self._callbacks.on_ampdu(self, pdu.header, pdu.lap_timer_s, pdu.accel_fl_x_mg, pdu.accel_fl_y_mg,
                                 pdu.accel_fl_z_mg)


class ProtocolBase:
    def __init__(self) -> None:
        pass

    def pack_raw(self) -> bytes:
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


class ProtocolAAPDU(ProtocolBase):
    def __init__(self) -> None:
        """
        Initialise a protocol AAPDU instance
        """
        super().__init__()

        self.header = ProtocolHeader()
        self.header.frame_type = AAPDU
        self.evo_scanner1 = 0
        self.evo_scanner2 = 0
        self.evo_scanner3 = 0
        self.evo_scanner4 = 0
        self.evo_scanner5 = 0
        self.evo_scanner6 = 0
        self.evo_scanner7 = 0

    def pack_raw(self) -> bytes:
        """
        Pack self to little-endian bytes.
        """
        temp = struct.pack("<HHHHHHH", self.evo_scanner1, self.evo_scanner2, self.evo_scanner3, self.evo_scanner4,
                           self.evo_scanner5, self.evo_scanner6, self.evo_scanner7)
        self.header.length = len(temp)
        return self.header.pack_raw() + temp

    def unpack_raw(self, buffer: bytes) -> None:
        """
        Unpack a buffer containing a little-endian header frame into self.
        :param buffer:  The buffer containing the header frame
        """
        self.header.unpack_raw(buffer[:12])
        self.evo_scanner1, self.evo_scanner2, self.evo_scanner3, self.evo_scanner4, \
        self.evo_scanner5, self.evo_scanner6, self.evo_scanner7 = struct.unpack("<HHHHHHH", buffer[12:])

    def pack_json(self) -> str:
        """
        Pack self to a JSON string.
        """
        return self.header.pack_json() + json.dumps({EVO_SCANNER1: self.evo_scanner1, EVO_SCANNER2: self.evo_scanner2,
                                                     EVO_SCANNER3: self.evo_scanner3, EVO_SCANNER4: self.evo_scanner4,
                                                     EVO_SCANNER5: self.evo_scanner5, EVO_SCANNER6: self.evo_scanner6,
                                                     EVO_SCANNER7: self.evo_scanner7})

    def unpack_json(self, buffer: str) -> None:
        """
        Unpack a JSON string into self.
        :param buffer:  The JSON string.
        """
        temp = json.loads(buffer)
        self.header.frame_type = temp[FRAME_TYPE]
        self.header.seq_num = temp[SEQ_NUM]
        self.header.epoch = temp[EPOCH]
        self.evo_scanner1 = temp[EVO_SCANNER1]
        self.evo_scanner2 = temp[EVO_SCANNER2]
        self.evo_scanner3 = temp[EVO_SCANNER3]
        self.evo_scanner4 = temp[EVO_SCANNER4]
        self.evo_scanner5 = temp[EVO_SCANNER5]
        self.evo_scanner6 = temp[EVO_SCANNER6]
        self.evo_scanner7 = temp[EVO_SCANNER7]

    def __str__(self) -> str:
        """
        Get a string  representation of self.
        """
        return str(self.header) + str({"EVO_SCANNER1": self.evo_scanner1, "EVO_SCANNER2": self.evo_scanner2,
                                       "EVO_SCANNER3": self.evo_scanner3, "EVO_SCANNER4": self.evo_scanner4,
                                       "EVO_SCANNER5": self.evo_scanner5, "EVO_SCANNER6": self.evo_scanner6,
                                       "EVO_SCANNER7": self.evo_scanner7})

    def __eq__(self, other: ProtocolAAPDU) -> bool:
        return self.header == other.header and self.evo_scanner1 == other.evo_scanner1 and \
               self.evo_scanner2 == other.evo_scanner2 and self.evo_scanner3 == other.evo_scanner3 and \
               self.evo_scanner4 == other.evo_scanner4 and self.evo_scanner5 == other.evo_scanner5 and \
               self.evo_scanner6 == other.evo_scanner6 and self.evo_scanner7 == other.evo_scanner7


class ProtocolADPDU(ProtocolBase):
    def __init__(self) -> None:
        """
        Initialise a protocol ADPDU instance
        """
        super().__init__()

        self.header = ProtocolHeader()
        self.header.frame_type = ADPDU
        self.ecu_status = ECU_STATUS_DISCONNECTED
        self.engine_status = ENGINE_STATUS_OFF
        self.battery_status = BATTERY_STATUS_DISCONNECTED
        self.car_logging_status = CAR_LOGGING_STATUS_OFF

    def pack_raw(self) -> bytes:
        """
        Pack self to little-endian bytes.
        """
        temp = struct.pack("<BBBB", self.ecu_status, self.engine_status, self.battery_status, self.car_logging_status)
        self.header.length = len(temp)
        return self.header.pack_raw() + temp

    def unpack_raw(self, buffer: bytes) -> None:
        """
        Unpack a buffer containing a little-endian header frame into self.
        :param buffer:  The buffer containing the header frame
        """
        self.header.unpack_raw(buffer[:12])
        self.ecu_status, self.engine_status, self.battery_status, self.car_logging_status \
            = struct.unpack("<BBBB", buffer[12:])

    def pack_json(self) -> str:
        """
        Pack self to a JSON string.
        """
        return self.header.pack_json() + json.dumps({ECU_STATUS: self.ecu_status, ENGINE_STATUS: self.engine_status,
                                                     BATTERY_STATUS: self.battery_status,
                                                     CAR_LOGGING_STATUS: self.car_logging_status})

    def unpack_json(self, buffer: str) -> None:
        """
        Unpack a JSON string into self.
        :param buffer:  The JSON string.
        """
        temp = json.loads(buffer)
        self.header.frame_type = temp[FRAME_TYPE]
        self.header.seq_num = temp[SEQ_NUM]
        self.header.epoch = temp[EPOCH]
        self.ecu_status = temp[ECU_STATUS]
        self.engine_status = temp[ENGINE_STATUS]
        self.battery_status = temp[BATTERY_STATUS]
        self.car_logging_status = temp[CAR_LOGGING_STATUS]

    def __str__(self) -> str:
        """
        Get a string  representation of self.
        """
        return str(self.header) + str({"ECU_STATUS": self.ecu_status, "ENGINE_STATUS": self.engine_status,
                                       "BATTERY_STATUS": self.battery_status,
                                       "CAR_LOGGING_STATUS": self.car_logging_status})

    def __eq__(self, other: ProtocolADPDU) -> bool:
        return self.header == other.header and self.ecu_status == other.ecu_status and \
               self.engine_status == other.engine_status and self.battery_status == other.battery_status and \
               self.car_logging_status == other.car_logging_status


class ProtocolAPPDU(ProtocolBase):
    def __init__(self) -> None:
        """
        Initialise a protocol APPDU instance
        """
        super().__init__()

        self.header = ProtocolHeader()
        self.header.frame_type = APPDU
        self.injection_time = 0
        self.injection_duty_cycle = 0
        self.lambda_pid_adjust = 0
        self.lambda_pid_target = 0
        self.advance = 0

    def pack_raw(self) -> bytes:
        """
        Pack self to little-endian bytes.
        """
        temp = struct.pack("<HHHH", self.injection_time, self.injection_duty_cycle, self.lambda_pid_adjust,
                           self.lambda_pid_target)
        self.header.length = len(temp)
        return self.header.pack_raw() + temp

    def unpack_raw(self, buffer: bytes) -> None:
        """
        Unpack a buffer containing a little-endian header frame into self.
        :param buffer:  The buffer containing the header frame
        """
        self.header.unpack_raw(buffer[:12])
        self.injection_time, self.injection_duty_cycle, self.lambda_pid_adjust, self.lambda_pid_target = \
            struct.unpack("<HHHH", buffer[12:])

    def pack_json(self) -> str:
        """
        Pack self to a JSON string.
        """
        return self.header.pack_json() + json.dumps({INJECTION_TIME: self.injection_time,
                                                     INJECTION_DUTY_CYCLE: self.injection_duty_cycle,
                                                     LAMBDA_PID_ADJUST: self.lambda_pid_adjust,
                                                     LAMBDA_PID_TARGET: self.lambda_pid_target})

    def unpack_json(self, buffer: str) -> None:
        """
        Unpack a JSON string into self.
        :param buffer:  The JSON string.
        """
        temp = json.loads(buffer)
        self.header.frame_type = temp[FRAME_TYPE]
        self.header.seq_num = temp[SEQ_NUM]
        self.header.epoch = temp[EPOCH]
        self.injection_time = temp[INJECTION_TIME]
        self.injection_duty_cycle = temp[INJECTION_DUTY_CYCLE]
        self.lambda_pid_adjust = temp[LAMBDA_PID_ADJUST]
        self.lambda_pid_target = temp[LAMBDA_PID_TARGET]

    def __str__(self) -> str:
        """
        Get a string  representation of self.
        """
        return str(self.header) + str({"INJECTION_TIME": self.injection_time,
                                       "INJECTION_DUTY_CYCLE": self.injection_duty_cycle,
                                       "LAMBDA_PID_ADJUST": self.lambda_pid_adjust,
                                       "LAMBDA_PID_TARGET": self.lambda_pid_target})

    def __eq__(self, other: ProtocolAPPDU) -> bool:
        return self.header == other.header and self.injection_time == other.injection_time and \
               self.injection_duty_cycle == other.injection_duty_cycle and \
               self.lambda_pid_adjust == other.lambda_pid_adjust and \
               self.lambda_pid_target == other.lambda_pid_target


class ProtocolASPDU(ProtocolBase):
    def __init__(self) -> None:
        """
        Initialise a protocol APPDU instance
        """
        super().__init__()

        self.header = ProtocolHeader()
        self.header.frame_type = ASPDU
        self.ride_height_fl_cm = 0
        self.ride_height_fr_cm = 0
        self.ride_height_flw_cm = 0
        self.ride_height_rear_cm = 0

    def pack_raw(self) -> bytes:
        """
        Pack self to little-endian bytes.
        """
        temp = struct.pack("<hhhh", self.ride_height_fl_cm, self.ride_height_fr_cm, self.ride_height_flw_cm,
                           self.ride_height_rear_cm)
        self.header.length = len(temp)
        return self.header.pack_raw() + temp

    def unpack_raw(self, buffer: bytes) -> None:
        """
        Unpack a buffer containing a little-endian header frame into self.
        :param buffer:  The buffer containing the header frame
        """
        self.header.unpack_raw(buffer[:12])
        self.ride_height_fl_cm, self.ride_height_fr_cm, self.ride_height_flw_cm, self.ride_height_rear_cm = \
            struct.unpack("<hhhh", buffer[12:])

    def pack_json(self) -> str:
        """
        Pack self to a JSON string.
        """
        return self.header.pack_json() + json.dumps({RIDE_HEIGHT_FL_CM: self.ride_height_fl_cm,
                                                     RIDE_HEIGHT_FR_CM: self.ride_height_fr_cm,
                                                     RIDE_HEIGHT_FLW_CM: self.ride_height_flw_cm,
                                                     RIDE_HEIGHT_REAR_CM: self.ride_height_rear_cm})

    def unpack_json(self, buffer: str) -> None:
        """
        Unpack a JSON string into self.
        :param buffer:  The JSON string.
        """
        temp = json.loads(buffer)
        self.header.frame_type = temp[FRAME_TYPE]
        self.header.seq_num = temp[SEQ_NUM]
        self.header.epoch = temp[EPOCH]
        self.ride_height_fl_cm = temp[RIDE_HEIGHT_FL_CM]
        self.ride_height_fr_cm = temp[RIDE_HEIGHT_FR_CM]
        self.ride_height_flw_cm = temp[RIDE_HEIGHT_FLW_CM]
        self.ride_height_rear_cm = temp[RIDE_HEIGHT_REAR_CM]

    def __str__(self) -> str:
        """
        Get a string  representation of self.
        """
        return str(self.header) + str({"RIDE_HEIGHT_FL_CM": self.ride_height_fl_cm,
                                       "RIDE_HEIGHT_FR_CM": self.ride_height_fr_cm,
                                       "RIDE_HEIGHT_FLW_CM": self.ride_height_flw_cm,
                                       "RIDE_HEIGHT_REAR_CM": self.ride_height_rear_cm})

    def __eq__(self, other: ProtocolASPDU) -> bool:
        return self.header == other.header and self.ride_height_fl_cm == other.ride_height_fl_cm and \
               self.ride_height_fr_cm == other.ride_height_fr_cm and \
               self.ride_height_flw_cm == other.ride_height_flw_cm and \
               self.ride_height_rear_cm == other.ride_height_rear_cm


class ProtocolAMPDU(ProtocolBase):
    def __init__(self) -> None:
        """
        Initialise a protocol APMDU instance
        """
        super().__init__()

        self.header = ProtocolHeader()
        self.header.frame_type = AMPDU
        self.lap_timer_s = 0
        self.accel_fl_x_mg = 0
        self.accel_fl_y_mg = 0
        self.accel_fl_z_mg = 0

    def pack_raw(self) -> bytes:
        """
        Pack self to little-endian bytes.
        """
        temp = struct.pack("<ihhh", self.lap_timer_s, self.accel_fl_x_mg, self.accel_fl_y_mg,
                           self.accel_fl_z_mg)
        self.header.length = len(temp)
        return self.header.pack_raw() + temp

    def unpack_raw(self, buffer: bytes) -> None:
        """
        Unpack a buffer containing a little-endian header frame into self.
        :param buffer:  The buffer containing the header frame
        """
        self.header.unpack_raw(buffer[:12])
        self.lap_timer_s, self.accel_fl_x_mg, self.accel_fl_y_mg, self.accel_fl_z_mg = \
            struct.unpack("<ihhh", buffer[12:])

    def pack_json(self) -> str:
        """
        Pack self to a JSON string.
        """
        return self.header.pack_json() + json.dumps({LAP_TIMER_S: self.lap_timer_s, ACCEL_FL_X_MG: self.accel_fl_x_mg,
                                                     ACCEL_FL_Y_MG: self.accel_fl_y_mg,
                                                     ACCEL_FL_Z_MG: self.accel_fl_z_mg})

    def unpack_json(self, buffer: str) -> None:
        """
        Unpack a JSON string into self.
        :param buffer:  The JSON string.
        """
        temp = json.loads(buffer)
        self.header.frame_type = temp[FRAME_TYPE]
        self.header.seq_num = temp[SEQ_NUM]
        self.header.epoch = temp[EPOCH]
        self.lap_timer_s = temp[RIDE_HEIGHT_FL_CM]
        self.accel_fl_x_mg = temp[RIDE_HEIGHT_FR_CM]
        self.accel_fl_y_mg = temp[RIDE_HEIGHT_FLW_CM]
        self.accel_fl_z_mg = temp[RIDE_HEIGHT_REAR_CM]

    def __str__(self) -> str:
        """
        Get a string  representation of self.
        """
        return str(self.header) + str({"LAP_TIMER_S": self.lap_timer_s, "ACCEL_FL_X_MG": self.accel_fl_x_mg,
                                       "ACCEL_FL_Y_MG": self.accel_fl_y_mg, "ACCEL_FL_Z_MG": self.accel_fl_z_mg})

    def __eq__(self, other: ProtocolAMPDU) -> bool:
        return self.header == other.header and self.lap_timer_s == other.lap_timer_s and \
               self.accel_fl_x_mg == other.accel_fl_x_mg and \
               self.accel_fl_y_mg == other.accel_fl_y_mg and \
               self.accel_fl_z_mg == other.accel_fl_z_mg
