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

        type_mapping = {"enable": lambda x: x == "True",
                        "interval": lambda x: int(x),
                        "emulation": lambda x: x == "True",
                        "min": lambda x: int(x),
                        "max": lambda x: int(x),
                        "on_dash": lambda x: x == "True"
                        }

        for field in config_root.iter("database"):
            for config in field.findall("config"):
                self._db_config[config.attrib["name"]] = config.text

        for field in config_root.iter("sensors"):
            self._config["sensors"] = {}
            for sensor in field.findall("sensor"):
                self._config["sensors"][sensor.attrib["name"]] = {"config": {}, "meta": {}}

                for config in sensor.findall("config"):
                    if config.attrib["name"] in type_mapping:
                        self._config["sensors"][sensor.attrib["name"]]["config"][config.attrib["name"]] = \
                            type_mapping[config.attrib["name"]](config.text)
                    else:
                        self._config["sensors"][sensor.attrib["name"]]["config"][config.attrib["name"]] = config.text

                assert("enable" in self._config["sensors"][sensor.attrib["name"]]["config"])
                assert("group" in self._config["sensors"][sensor.attrib["name"]]["config"])

                for meta in sensor.findall("meta"):
                    if meta.attrib["name"] in type_mapping:
                        self._config["sensors"][sensor.attrib["name"]]["meta"][meta.attrib["name"]] = \
                            type_mapping[meta.attrib["name"]](meta.text)
                    else:
                        self._config["sensors"][sensor.attrib["name"]]["meta"][meta.attrib["name"]] = meta.text

                assert("min" in self._config["sensors"][sensor.attrib["name"]]["meta"])
                assert("max" in self._config["sensors"][sensor.attrib["name"]]["meta"])
                assert("on_dash" in self._config["sensors"][sensor.attrib["name"]]["meta"])

        for field in config_root.iter("server"):
            for config in field.findall("config"):
                self._config[config.attrib["name"]] = config.text

        assert("emulation" in self._config)
        assert("sensors" in self._config)
        assert("verbose" in self._config)

        assert("name" in self._db_config)
        assert("interval" in self._db_config)

        self._config["emulation"] = self._config["emulation"] == "True"
        self._db_config["interval"] = float(self._db_config["interval"])

    def _initialise_database(self):
        for sensor, config in self._config["sensors"].items():
            self._database.create_sensor_table(sensor, ["value"])

    def _save_sensor_data_to_database(self, sensor_data: list):
        # Insert the data into database.
        for sensor in sensor_data:
            name, time_ms, value = sensor
            self._database.insert_sensor_data(name, time_ms, (value,))
            self._logger.debug(f"db <- {name} {time_ms} {value}")

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

        asyncio.get_event_loop().create_task(self._commit_database())
        try:
            asyncio.get_event_loop().run_forever()
        finally:
            print("End")

    def _restful_serve(self, request: restful.RestfulRequest) -> tuple:
        self._logger.info(f"Serving: {request}")

        request_handlers = {"GET": self._restful_server_get_request}

        if request.get_type() in request_handlers:
            try:
                response, epoch = request_handlers[request.get_type()](request, request.get_filters())
            except Exception as exc:
                raise exc
        else:
            raise NotImplementedError

        return response, epoch

    def _restful_server_get_request(self, request: restful.RestfulRequest, filters: dict) -> tuple:
        filters = {"amount": 99}
        response = {}
        dataset_handlers = {"sensors": self._restful_serve_sensors,
                            "meta": self._restful_server_meta}

        for fil in request.get_filters():
            name, val = fil
            if name == "amount":
                filters["amount"] = val
            elif name == "timesince":
                filters["timesince"] = val
            else:
                raise NotImplementedError

        if request.get_datasets()[0] in dataset_handlers:
            try:
                response, epoch = dataset_handlers[request.get_datasets()[0]](request, filters)
            except Exception as exc:
                raise exc
        else:
            raise NotImplementedError

        return response, epoch

    def _restful_server_meta(self, request: restful.RestfulRequest, filters: dict) -> tuple:
        response = {}

        if request.get_datasets()[1] == "sensors":
            for sensor, data in self._config["sensors"].items():
                if data["config"]["enable"]:
                    if data["config"]["group"] not in response:
                        response[data["config"]["group"]] = {}
                    response[data["config"]["group"]][sensor] = self._config["sensors"][sensor]["meta"]
        else:
            raise FileNotFoundError

        return response, time.time()

    def _restful_serve_sensors(self, request: restful.RestfulRequest, filters: dict) -> tuple:
        response = {}
        epoch = 0

        if len(request.get_datasets()) == 1:
            # /sensors
            for sensor, data in self._config["sensors"].items():
                if data["config"]["enable"]:
                    if data["config"]["group"] not in response:
                        response[data["config"]["group"]] = {}
                    sensor_data = self._restful_serve_sensor_get_data(sensor, filters)
                    if len(sensor_data) > 0:
                        response[data["config"]["group"]][sensor] = sensor_data
                        if sensor_data[-1]["time"] > epoch:
                            epoch = sensor_data[-1]["time"]
        elif len(request.get_datasets()) == 2:
            # e.g. /sensors/core
            if request.get_datasets()[1] in self._config["sensors"]:
                response[request.get_datasets()[1]] = {}

                for sensor, data in self._config["sensors"].items():
                    if data["config"]["enable"]:
                        if data["config"]["group"] == request.get_datasets()[1]:
                            sensor_data = self._restful_serve_sensor_get_data(sensor, filters)
                            if len(sensor_data) > 0:
                                response[data["config"]["group"]][sensor] = sensor_data
                                if sensor_data[-1]["time"] > epoch:
                                    epoch = sensor_data[-1]["time"]
            else:
                raise FileNotFoundError
        else:
            raise FileNotFoundError

        return response, epoch

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

    async def _commit_database(self):
        while True:
            await asyncio.sleep(self._db_config["interval"])

            self._database.commit()

    def __enter__(self) -> Server:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._logger.error(f"{exc_type}\n{exc_val}\n{exc_tb}")
