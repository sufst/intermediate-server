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

import common
import protocol
import protocol_factory
import restful
import serverdatabase
import caremulator
import xml.etree.ElementTree


class Server:
    def __init__(self):
        """
        Create an instance of the Intermediate server.

        The intermediate server provides the service of processing protocol PDUs over XBee from the car (or over a
        socket for testing or future car communications) and extracts the data fields contained within them. The
        data fields are staged in a database and are accessible through the RESTful API over WebSockets.

        The staging database is consistent on file and therefore data can be accessed through different runs of the
        server.

        The configuration of the intermediate server is done through the config.xml configuration file.
        """
        self._parse_configuration()

        self._logger = common.get_logger(type(self).__name__, self._config["verbose"])

        self._logger.info(f"Configuration: {self._config}")

        self._restful = restful.Restful()
        if self._config["emulation"]:
            self._database = serverdatabase.ServerDatabase("emulation")
        else:
            self._database = serverdatabase.ServerDatabase(self._db_config["name"])
        self._initialise_database()
        self._initialise_protocol()

    def _parse_configuration(self):
        config_root = xml.etree.ElementTree.parse("config.xml").getroot()
        self._config = {}
        self._db_config = {}

        for field in config_root.iter("database"):
            for config in field.findall("config"):
                self._db_config[config.attrib["name"]] = config.text

        for field in config_root.iter("sensors"):
            self._config["sensors"] = {}
            for sensor in field.findall("sensor"):
                self._config["sensors"][sensor.attrib["name"]] = {}
                for config in sensor.findall("config"):
                    self._config["sensors"][sensor.attrib["name"]][config.attrib["name"]] = config.text
                    if config.attrib["name"] == "enable":
                        self._config["sensors"][sensor.attrib["name"]][config.attrib["name"]] = \
                            self._config["sensors"][sensor.attrib["name"]][config.attrib["name"]] == "True"

        for field in config_root.iter("server"):
            for config in field.findall("config"):
                self._config[config.attrib["name"]] = config.text

        assert("emulation" in self._config)
        assert("sensors" in self._config)
        assert("verbose" in self._config)

        assert("name" in self._db_config)

        self._config["emulation"] = self._config["emulation"] == "True"

    def _initialise_database(self):
        for sensor, config in self._config["sensors"].items():
            self._database.create_sensor_table(sensor, ["value"])

    def _save_sensor_data_to_database(self, sensor_data: list):
        # Insert the data into database.
        for sensor in sensor_data:
            name, time_ms, value = sensor
            self._database.insert_sensor_data(name, time_ms, (value,))
            self._logger.debug(f"db <- {name} {time_ms} {value}")

        self._database.commit()

    def _initialise_protocol(self):
        self._protocol = protocol.Protocol()
        self._protocol_factory = protocol_factory.ProtocolFactory()

    async def _protocol_serve(self, client: protocol_factory.ProtocolClient):
        self._logger.info("Serving protocol client")
        running = True

        while running:
            try:
                data = await client.recv()
                self._logger.debug(f"Client <- {data}")
                self._protocol.decode_to(data, self._protocol_serve_fields)
            except Exception as error:
                self._logger.warning(error)
                running = False

    def _protocol_serve_fields(self, fields: dict):
        self._logger.debug(fields)

        # If the fields doesn't include an epoch field, then take the server epoch as epoch.
        if "epoch" in fields:
            epoch = fields["epoch"]
        else:
            epoch = time.time()

        # Remove the epoch field so we can just loop fields
        del fields["epoch"]

        sensor_data = []
        for name, value in fields.items():
            sensor_data.extend([(name, epoch, value)])

        self._save_sensor_data_to_database(sensor_data)

    def serve_forever(self) -> None:
        """
        Serve the server forever.

        This starts the RESTful API and protocol factory or emulation (if enabled).
        """
        self._restful.serve(self._restful_serve)
        if self._config["emulation"]:
            emulator = caremulator.CarEmulator(self._database)
            emulator.serve()
        else:
            self._protocol_factory.serve(self._protocol_serve)

        asyncio.get_event_loop().run_forever()

    def _restful_serve(self, request: restful.RestfulRequest) -> dict:
        self._logger.info(f"Serving: {request}")

        filters = {"amount": 99}
        response = {}

        for fil in request.get_filters():
            name, val = fil
            if name == "amount":
                filters["amount"] = val
            elif name == "timesince":
                filters["timesince"] = val
            else:
                raise NotImplementedError

        if request.get_type() == "GET":
            if request.get_datasets()[0] == "sensors":
                try:
                    response = self._restful_serve_sensors(request, filters)
                except Exception as exc:
                    raise exc
        else:
            raise NotImplementedError

        return response

    def _restful_serve_sensors(self, request: restful.RestfulRequest, filters: dict) -> dict:
        response = {}

        if len(request.get_datasets()) == 1:
            # /sensors
            for sensor, config in self._config["sensors"].items():
                if config["enable"]:
                    if config["group"] not in response:
                        response[config["group"]] = {}
                    response[config["group"]][sensor] = self._restful_serve_sensor_get_data(sensor, filters)
        elif len(request.get_datasets()) == 2:
            # e.g. /sensors/core
            if request.get_datasets()[1] in self._config["sensors"]:
                response[request.get_datasets()[1]] = {}

                for sensor, config in self._config["sensors"].items():
                    if config["enable"]:
                        if config["group"] == request.get_datasets()[1]:
                            response[config["group"]][sensor] = self._restful_serve_sensor_get_data(sensor, filters)
            else:
                raise FileNotFoundError
        else:
            raise FileNotFoundError

        return response

    def _restful_serve_sensor_get_data(self, sensor: str, filters: dict) -> list:
        data = []
        if "amount" in filters and not "timesince" in filters:
            data_raw = self._database.select_sensor_data_top_n_entries(sensor, filters["amount"])
        elif "amount" not in filters and "timesince" in filters:
            data_raw = self._database.select_sensor_data_between_times(
                sensor, [filters["timesince"], time.time()])
        elif "amount" in filters and "timesince" in filters:
            data_raw = self._database.select_sensor_data_top_n_entries_and_between_times(
                sensor, filters["amount"], [filters["timesince"], time.time()])
        else:
            data_raw = []

        for sensor_time, sensor_val in data_raw:
            data.extend([{"time": sensor_time, "value": sensor_val}])

        # RESTful clients want the data from oldest -> earliest (but the db get returns it earliest -> oldest).
        data.reverse()

        return data

    def __enter__(self) -> Server:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._logger.error(f"{exc_type}\n{exc_val}\n{exc_tb}")
