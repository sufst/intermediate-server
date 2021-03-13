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

import websockets

import common
import xml.etree.ElementTree


class RestfulRequest:
    def __init__(self, request_str: str):
        """
        Sub class for encapsulating a RESTful request and response.
        :param request_str: The RESTful request string received.
        """
        self._request_str = request_str

        self._dataset, self._filters, self._type = None, [], None

        self._decode_request()

    def _decode_request(self) -> None:
        """
        Decode the RESTful request string to determine the type, dataset, and filters wanted.
        """
        # Decode GET /sensors/RPM?timesince=<epoch>&amount=<n>
        split_space = self._request_str.split(" ")
        self._type = split_space[0]
        split_question = split_space[1].split("?")
        self._dataset = split_question[0]
        self._datasets = self._dataset.split("/")[1:]
        split_and = split_question[1].split("&")

        for fil in split_and:
            self._filters.extend([tuple(fil.split("="))])

    def get_type(self) -> str:
        """
        Get the type of the request.
        :return: The type.
        """
        return self._type

    def get_dataset(self) -> str:
        """
        Get the dataset (in a single string combined).
        :return: The dataset.
        """
        return self._dataset

    def get_datasets(self) -> list:
        """
        Get the datasets (in a list form )
        :return:
        """
        return self._datasets

    def get_filters(self) -> list:
        """
        Get the filters (in the form of a list of tuples(filter, value)).
        :return:
        """
        return self._filters

    def __str__(self) -> str:
        return str({"type": self._type, "dataset": self._dataset, "filters": self._filters})


class Restful:
    def __init__(self):
        """
        Initialise the RESTful server to handle RESTful requests over the websocket.

        The RESTful server will invoke the callable passed in def server with the request in the form
        of the RestfulRequest sub class. The RestfulRequest sub class provides the type, datasets, and filters
        the RESTful requests is made up with. A response can be sent back to the client by returning a Dict
        in the callable function.
        """
        self._parse_configuration()

        self._logger = common.get_logger("Restful", self._config["verbose"])

        self._logger.info(f"Configuration: {self._config}")

        self._server = websockets.serve(self._websocket_serve, self._config["url"], self._config["port"])
        self._request_callable = None

    def _parse_configuration(self):
        config_root = xml.etree.ElementTree.parse("config.xml").getroot()
        self._config = {}

        for field in config_root.iter("RESTful"):
            for config in field.findall("config"):
                self._config[config.attrib["name"]] = config.text

        assert("url" in self._config)
        assert("port" in self._config)
        assert("verbose" in self._config)
        assert("keep_alive" in self._config)

        self._config["port"] = int(self._config["port"])
        self._config["keep_alive"] = self._config["keep_alive"] == "True"

    def serve(self, request_callable):
        """
        Start the server to serve network requests.
        :param request_callable: Callback function for serving received requests.
        """
        self._request_callable = request_callable

        asyncio.get_event_loop().run_until_complete(self._server)
        self._logger.info(f"Serving on {self._config['url']}:{self._config['port']}")

    async def _websocket_serve(self, websocket, path: str):
        """
        Serve a new websocket client.
        :param websocket: The new websocket object.
        :param path: The accessed path from the client.
        """
        try:
            while self._config["keep_alive"]:
                request = await websocket.recv()
                self._logger.info(f"Got request: {request}")

                response = {"status": 200, "result": {}, "epoch": 0}

                try:
                    request = RestfulRequest(request)
                except Exception as error:
                    self._logger.error(error)
                    response["status"] = 400
                else:
                    try:
                        response["result"] = self._request_callable(request)

                        # Find the most recent epoch
                        for g_name, group in response["result"].items():
                            for s_name, sensor in group.items():
                                if sensor[-1]["time"] > response["epoch"]:
                                    response["epoch"] = sensor[-1]["time"]

                    except NotImplementedError:
                        response["status"] = 501
                    except SystemError:
                        response["status"] = 500
                    except FileNotFoundError:
                        response["status"] = 404

                self._logger.info(f"Response <- {response}")
                await websocket.send(json.dumps(response))

            websocket.close()
        except websockets.ConnectionClosedOK:
            pass
        except websockets.ConnectionClosedError:
            pass
