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
import struct
import xml.etree.ElementTree

import common
import protocol_factory


class Protocol:
    def __init__(self):
        """
        Initialise the protocol.

        The Protocol class parses the schema definition in config.xml and extracts the corresponding PDUs
        contained within it.
        """
        self._parse_configuration()

        self._logger = common.get_logger("Protocol", self._config["verbose"])

        self._logger.info(f"Configuration: {self._config}")
        self._logger.info(f"Schema: {self._schema}")

    def _parse_configuration(self):
        config_root = xml.etree.ElementTree.parse("config.xml").getroot()
        self._config = {}
        self._schema = {}

        for field in config_root.iter("schema"):
            for config in field.findall("config"):
                self._config[config.attrib["name"]] = config.text

        assert("verbose" in self._config)

        for field in config_root.iter("schema"):
            for header in field.findall("header"):
                self._schema["header"] = {}
                for entry in header.findall("field"):
                    self._schema["header"][entry.attrib["name"]] = {}
                    for prop in entry.findall("property"):
                        self._schema["header"][entry.attrib["name"]][prop.attrib["name"]] = prop.text
                    assert("C_type" in self._schema["header"][entry.attrib["name"]])
            for pdu in field.findall("pdu"):
                self._schema[pdu.attrib["name"]] = {}
                for prop in pdu.findall("property"):
                    self._schema[pdu.attrib["name"]][prop.attrib["name"]] = prop.text

                assert("frame_id" in self._schema[pdu.attrib["name"]])
                assert("enable" in self._schema[pdu.attrib["name"]])
                assert("header" in self._schema[pdu.attrib["name"]])

                self._schema[pdu.attrib["name"]]["enable"] = self._schema[pdu.attrib["name"]]["enable"] == "True"
                self._schema[pdu.attrib["name"]]["header"] = self._schema[pdu.attrib["name"]]["header"] == "True"

                for entry in pdu.findall("field"):
                    self._schema[pdu.attrib["name"]][entry.attrib["name"]] = {}
                    for prop in entry.findall("property"):
                        self._schema[pdu.attrib["name"]][entry.attrib["name"]][prop.attrib["name"]] = prop.text

                    assert("C_type" in self._schema[pdu.attrib["name"]][entry.attrib["name"]])


