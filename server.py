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

import asyncio
import time
from typing import Optional

import common
import protocol
import protocol_factory
import restful
import serverdatabase
import caremulator
import xml.etree.ElementTree


class ServerClient:
    def __init__(self, client_type: int, sw_ver: int, client_name: str, factory: protocol_factory.ProtocolFactoryBase):
        self.client_type = client_type
        self.client_name = client_name
        self.sw_ver = sw_ver
        self.factory = factory


class Server:
    def __init__(self):
        """
        Initialise the Server singleton instance.
        """
        self._parse_configuration()

        self._logger = common.get_logger(type(self).__name__, self._config["verbose"])

        self._logger.info(f"Configuration: {self._config}")

        self._protocol = None
        self._protocol_callbacks = protocol.ProtocolCallbacks()
        self._protocol_callbacks.on_connection = self._on_connection
        self._protocol_callbacks.on_lost = self._on_lost
        self._protocol_callbacks.on_aipdu = self._on_aipdu
        self._protocol_callbacks.on_acpdu = self._on_acpdu
        self._protocol_callbacks.on_aapdu = self._on_aapdu
        self._protocol_callbacks.on_adpdu = self._on_adpdu
        self._protocol_callbacks.on_appdu = self._on_appdu
        self._protocol_callbacks.on_aspdu = self._on_aspdu
        self._protocol_callbacks.on_ampdu = self._on_ampdu

        self._event_loop = None
        self._on_stop = None

        self._restful = restful.Restful()
        if self._config["emulation"]:
            self._database = serverdatabase.ServerDatabase("emulation")
        else:
            self._database = serverdatabase.ServerDatabase(self._config["database"])
        self._initialise_database()

        self._car_clients = {}
        self._gui_clients = {}

    def _parse_configuration(self):
        config_root = xml.etree.ElementTree.parse("config.xml").getroot()
        self._config = {}

        for field in config_root.iter("server"):
            for config in field.findall("config"):
                self._config[config.attrib["name"]] = config.text

        for field in config_root.iter("XBee"):
            for config in field.findall("config"):
                self._config[config.attrib["name"]] = config.text

        assert("ip" in self._config)
        assert("port" in self._config)
        assert("emulation" in self._config)
        assert("baud" in self._config)
        assert("com" in self._config)
        assert("mac" in self._config)
        assert("verbose" in self._config)
        assert("database" in self._config)

        self._config["port"] = int(self._config["port"])
        self._config["emulation"] = bool(self._config["ip"])
        self._config["baud"] = int(self._config["baud"])

    def _initialise_database(self) -> None:
        """
        Initialise the staging database.
        """
        sensors = ["rpm", "water_temp_c", "tps_perc", "battery_mv", "ext_5v_mv",
                   "fuel_flow", "lambda", "speed_kph", "evo_scan_1", "evo_scan_2",
                   "evo_scan_3", "evo_scan_4", "evo_scan_5", "evo_scan_6", "evo_scan_7",
                   "status_ecu_connected", "status_engine", "status_battery", "status_logging",
                   "inj_time", "inj_duty_cycle", "lambda_pid_adj", "lambda_pid_target",
                   "advance", "ride_height_fl_cm", "ride_height_fr_cm", "ride_height_flw_cm",
                   "ride_height_rear_cm", "lap_time_s", "accel_fl_x_mg", "accel_fl_y_mg",
                   "accel_fl_z_mg"]

        for sensor in sensors:
            self._database.create_sensor_table(sensor, ["value"])

    def _save_sensor_data_to_database(self, sensor_data: list) -> None:
        """
        Save a list of sensor data to the staging database.
        :param sensor_data: The list of sensor data. (name, time, values).
        """
        # Insert the data into database.
        for sensor in sensor_data:
            name, time_ms, value = sensor
            self._database.insert_sensor_data(name, time_ms, (value,))

        self._database.commit()

    def __enter__(self) -> Server:
        """
        Enter for use with "with as"
        """
        return self

    def _on_connection(self, factory: protocol_factory.ProtocolFactoryBase) -> None:
        """
        Invoked when a factory has made a new connection.
        :param factory: The factory that has a new connection.
        """
        self._logger.info(f"Handling connection from factory {factory.__hash__()}")

    def _on_lost(self, factory: protocol_factory.ProtocolFactoryBase, exc: Optional[Exception]) -> None:
        """
        Invoked when a factory has lost its connection.
        :param factory: The factory that has lost its connection.
        :param exc:     Any error that caused the lost.
        """
        self._logger.info(f"Handling lost from factory {factory.__hash__()}")
        fact_hash = factory.__hash__()
        if fact_hash in self._gui_clients:
            del self._gui_clients[fact_hash]
        elif fact_hash in self._car_clients:
            del self._car_clients[fact_hash]

    def _on_aipdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  client_type: int, sw_ver: int, client_name: str) -> None:
        """
        Invoked when a factory has received a AIPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling AIPDU from factory {factory.__hash__()}")
        self._protocol.write_aipdu(factory, client_type, sw_ver, client_name)

        if not factory.__hash__() in self._car_clients or not factory.__hash__() in self._gui_clients:
            self._logger.info(f"New client type {client_type} saving factory {factory.__hash__()} for {client_name}")
            # Store the client locally.
            client = ServerClient(client_type, sw_ver, client_name, factory)
            if client_type == protocol.CAR or client_type == protocol.CAR_EMULATOR:
                self._car_clients[factory.__hash__()] = client
            else:
                self._gui_clients[factory.__hash__()] = client

    def _on_acpdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader, rpm: int,
                  water_temp_c: int, tps_perc: int, battery_mv: int, external_5v_mv: int, fuel_flow: int,
                  lambda_value: int, speed_kph: int) -> None:
        """
        Invoked when a factory has received a ACPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling ACPDU from factory {factory.__hash__()}")

        time_ms = int(time.time() * 1000)
        sensor_data = [("rpm", time_ms, rpm), ("water_temp_c", time_ms, water_temp_c),
                       ("tps_perc", time_ms, tps_perc), ("battery_mv", time_ms, battery_mv),
                       ("ext_5v_mv", time_ms, external_5v_mv), ("fuel_flow", time_ms, fuel_flow),
                       ("lambda", time_ms, lambda_value), ("speed_kph", time_ms, speed_kph)]

        # Insert the data into database.
        self._save_sensor_data_to_database(sensor_data)

        for _, client in self._gui_clients.items():
            self._logger.info(
                f"Routing ACPDU to client {client.client_name} through factory {client.factory.__hash__()}")
            self._protocol.write_acpdu(client.factory, rpm, water_temp_c, tps_perc, battery_mv, external_5v_mv,
                                       fuel_flow, lambda_value, speed_kph)

    def _on_aapdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  evo_scanner1: int, evo_scanner2: int, evo_scanner3: int, evo_scanner4: int, evo_scanner5: int,
                  evo_scanner6: int, evo_scanner7: int) -> None:
        """
        Invoked when a factory has received a AAPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling AAPDU from factory {factory.__hash__()}")

        time_ms = int(time.time() * 1000)
        sensor_data = [("evo_scan_1", time_ms, evo_scanner1), ("evo_scan_2", time_ms, evo_scanner2),
                       ("evo_scan_3", time_ms, evo_scanner3), ("evo_scan_4", time_ms, evo_scanner4),
                       ("evo_scan_5", time_ms, evo_scanner5), ("evo_scan_6", time_ms, evo_scanner6),
                       ("evo_scan_7", time_ms, evo_scanner7)]

        # Insert the data into database.
        self._save_sensor_data_to_database(sensor_data)

        for _, client in self._gui_clients.items():
            self._logger.info(
                f"Routing AAPDU to client {client.client_name} through factory {client.factory.__hash__()}")
            self._protocol.write_aapdu(client.factory, evo_scanner1, evo_scanner2, evo_scanner3, evo_scanner4,
                                       evo_scanner5, evo_scanner6, evo_scanner7)

    def _on_adpdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader, ecu_status: int,
                  engine_status: int, battery_status: int, car_logging_status: int) -> None:
        """
        Invoked when a factory has received a ADPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling ADPDU from factory {factory.__hash__()}")

        time_ms = int(time.time() * 1000)
        sensor_data = [("status_ecu_connected", time_ms, ecu_status),
                       ("status_engine", time_ms, engine_status),
                       ("status_battery", time_ms, battery_status),
                       ("status_logging", time_ms, car_logging_status)]

        # Insert the data into database.
        self._save_sensor_data_to_database(sensor_data)

        for _, client in self._gui_clients.items():
            self._logger.info(
                f"Routing ADPDU to client {client.client_name} through factory {client.factory.__hash__()}")
            self._protocol.write_adpdu(client.factory, ecu_status, engine_status, battery_status, car_logging_status)

    def _on_appdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  injection_time: int, injection_duty_cycle: int, lambda_pid_adjust: int, lambda_pid_target: int,
                  advance: int) -> None:
        """
        Invoked when a factory has received a APPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling APPDU from factory {factory.__hash__()}")

        time_ms = int(time.time() * 1000)
        sensor_data = [("inj_time", time_ms, injection_time),
                       ("inj_duty_cycle", time_ms, injection_duty_cycle),
                       ("lambda_pid_adj", time_ms, lambda_pid_adjust),
                       ("lambda_pid_target", time_ms, lambda_pid_target),
                       ("advance", time_ms, advance)]

        # Insert the data into database.
        self._save_sensor_data_to_database(sensor_data)

        for _, client in self._gui_clients.items():
            self._logger.info(
                f"Routing APPDU to client {client.client_name} through factory {client.factory.__hash__()}")
            self._protocol.write_appdu(client.factory, injection_time, injection_duty_cycle, lambda_pid_adjust,
                                       lambda_pid_target, advance)

    def _on_aspdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  ride_height_fl_cm: int, ride_height_fr_cm: int, ride_height_flw_cm: int,
                  ride_height_rear_cm: int) -> None:
        """
        Invoked when a factory has received a ASPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling ASPDU from factory {factory.__hash__()}")

        time_ms = int(time.time() * 1000)
        sensor_data = [("ride_height_fl_cm", time_ms, ride_height_fl_cm),
                       ("ride_height_fr_cm", time_ms, ride_height_fr_cm),
                       ("ride_height_flw_cm", time_ms, ride_height_flw_cm),
                       ("ride_height_rear_cm", time_ms, ride_height_rear_cm)]

        # Insert the data into database.
        self._save_sensor_data_to_database(sensor_data)

        for _, client in self._gui_clients.items():
            self._logger.info(
                f"Routing ASPDU to client {client.client_name} through factory {client.factory.__hash__()}")
            self._protocol.write_aspdu(client.factory, ride_height_fl_cm, ride_height_fr_cm, ride_height_flw_cm,
                                       ride_height_rear_cm)

    def _on_ampdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  lap_timer_s: int, accel_fl_x_mg: int, accel_fl_y_mg: int, accel_fl_z_mg: int) -> None:
        """
        Invoked when a factory has received a AMPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling AMPDU from factory {factory.__hash__()}")

        time_ms = int(time.time() * 1000)
        sensor_data = [("lap_time_s", time_ms, lap_timer_s),
                       ("accel_fl_x_mg", time_ms, accel_fl_x_mg),
                       ("accel_fl_y_mg", time_ms, accel_fl_y_mg),
                       ("accel_fl_z_mg", time_ms, accel_fl_z_mg)]

        # Insert the data into database.
        self._save_sensor_data_to_database(sensor_data)

        for _, client in self._gui_clients.items():
            self._logger.info(
                f"Routing AMPDU to client {client.client_name} through factory {client.factory.__hash__()}")
            self._protocol.write_ampdu(client.factory, lap_timer_s, accel_fl_x_mg, accel_fl_y_mg, accel_fl_z_mg)

    def run(self) -> None:
        """
        Run the server asyncio loop
        """
        self._restful.serve(self._restful_serve)
        if self._config["emulation"]:
            emulator = caremulator.CarEmulator(self._database)
            emulator.serve()
        else:
            asyncio.get_event_loop().create_task(self._run())

        asyncio.get_event_loop().run_forever()

    async def _run(self) -> asyncio.coroutine:
        """
        The asyncio event loop for the server.
        """
        self._logger.info("Running")
        self._event_loop = asyncio.get_running_loop()
        self._on_stop = asyncio.Future()

        self._logger.info(f"Creating Protocol {self._config['ip']}:{self._config['port']}")
        self._protocol = protocol.Protocol(ip=self._config["ip"], port=self._config["port"], com=self._config["com"],
                                           baud=self._config["baud"], mac=self._config["mac"],
                                           callbacks=self._protocol_callbacks, protocol_type=protocol.SERVER,
                                           event_loop=self._event_loop, verbose=self._config["verbose"])
        self._protocol.run()

        try:
            await self._on_stop
        finally:
            self._logger.info("Stopped")

    async def _restful_serve(self, request: restful.RestfulRequest):
        """
        Serve a RESTful request.
        :param request: The RESTful request.
        """
        sensors = ["rpm", "water_temp_c", "tps_perc", "battery_mv", "ext_5v_mv",
                   "fuel_flow", "lambda", "speed_kph", "evo_scan_1", "evo_scan_2",
                   "evo_scan_3", "evo_scan_4", "evo_scan_5", "evo_scan_6", "evo_scan_7",
                   "status_ecu_connected", "status_engine", "status_battery", "status_logging",
                   "inj_time", "inj_duty_cycle", "lambda_pid_adj", "lambda_pid_target",
                   "advance", "ride_height_fl_cm", "ride_height_fr_cm", "ride_height_flw_cm",
                   "ride_height_rear_cm", "lap_time_s", "accel_fl_x_mg", "accel_fl_y_mg",
                   "accel_fl_z_mg"]

        self._logger.info(f"Serving: {request}")

        response = {}
        amount = 99
        timesince = None

        for fil in request.get_filters():
            name, val = fil
            if name == "amount":
                amount = val
            elif name == "timesince":
                timesince = val

        if request.get_type() == "GET":
            if request.get_datasets()[0] == "sensors":
                if len(request.get_datasets()) == 1:
                    # /sensors
                    for sensor in sensors:
                        sensor_data = self._database.select_sensor_data_top_n_entries(sensor, amount)
                        if len(sensor_data) > 0:
                            response[sensor] = []
                            for sensor_time, sensor_val in sensor_data:
                                response[sensor].extend([{"time": sensor_time, "value": sensor_val}])

        await request.respond(response)

    def __exit__(self, exc_type: Optional[Exception], exc_val: Optional[Exception], exc_tb: Optional[Exception]) \
            -> None:
        """
        Exit for use with "with as"
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        """
        if exc_type is not None:
            self._logger.error(f"{exc_type}\n{exc_val}\n{exc_tb}")
