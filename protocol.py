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


class ProtocolPDU:
    def __init__(self, name: str, pdu: dict):
        """
        Sub class to encapsulate a PDU.

        Each PDU defined within the schema will each have a corresponding instance of this class
        associated with it. The class is used as a helper for decoding and parsing of PDUs from streams.
        :param name: The name of the PDU.
        :param pdu: The dictionary containing the configuration of the PDU.
        """
        self._name = name
        self._pdu = pdu

        self._parse_pdu()

    def _parse_pdu(self) -> None:
        self._fields_names = []
        self._fields = {}
        self._length = 0
        self._struct_format = "<"

        c_type_lengths = {"c": 1, "b": 1, "B": 1, "?": 1, "h": 2, "H": 2, "i": 4, "I": 4,
                          "l": 4, "L": 4, "f": 4, "d": 8, "q": 8, "Q": 8}

        for name, prop in self._pdu.items():
            for prop_name, prop_value in prop.items():
                if prop_name == "C_type":
                    self._fields_names.extend([name])
                    self._length += c_type_lengths[prop_value]
                    self._struct_format += prop_value

    def get_length(self) -> int:
        """
        Get the length (in bytes) of the PDU.
        """
        return self._length

    def decode(self, bytes_in: bytes) -> None:
        """
        Decode the PDU from the bytes object.
        :param bytes_in: Bytes to decode the PDU from.
        """
        values = iter(struct.unpack(self._struct_format, bytes_in))

        for field in self._fields_names:
            self._fields[field] = next(values)

    def get_fields_values(self) -> dict:
        """
        Get the fields and values of the decoded PDU.

        The dictionary returned is in the form of {<field>: value, ...}.
        """
        return self._fields


class Protocol:
    def __init__(self):
        """
        Initialise the protocol.

        The Protocol class parses the schema definition in config.xml and extracts the corresponding PDUs
        contained within it.

        Once the Protocol class has been configured with the defined PDUs, the decode() function can be used
        to decode a byte object to extract all PDUs that are contained within it. The fields within the PDUs
        are then returned as a dictionary to the callable as the sole argument for handling. The PDUs that
        were decoded are abstracted away to just their containing fields (as these are what are important).
        """
        self._parse_configuration()

        self._logger = common.get_logger("Protocol", self._config["verbose"])

        self._logger.info(f"Configuration: {self._config}")
        self._logger.info(f"Schema: {self._schema}")

        self._construct_protocol()

    def _construct_protocol(self) -> None:
        self._pdu = {}

        for name, pdu in self._schema.items():
            self._pdu[pdu["id"]] = ProtocolPDU(name, pdu["fields"])

    def _parse_configuration(self) -> None:
        config_root = xml.etree.ElementTree.parse("config.xml").getroot()
        self._config = {}
        self._schema = {}

        for field in config_root.iter("schema"):
            for config in field.findall("config"):
                self._config[config.attrib["name"]] = config.text

            assert("verbose" in self._config)
            assert("start_byte" in self._config)

            self._config["start_byte"] = int(self._config["start_byte"])

            for pdu in field.findall("pdu"):
                self._schema[pdu.attrib["name"]] = {"id": int(pdu.attrib["id"]), "fields": {}}

                for entry in pdu.findall("field"):
                    self._schema[pdu.attrib["name"]]["fields"][entry.attrib["name"]] = {}
                    for prop in entry.findall("property"):
                        self._schema[pdu.attrib["name"]]["fields"][entry.attrib["name"]][prop.attrib["name"]] = prop.text

                    assert("C_type" in self._schema[pdu.attrib["name"]]["fields"][entry.attrib["name"]])

    def decode_to(self, stream: bytes, handler: callable) -> None:
        """
        Decode all PDUs from a byte stream. Each PDU decoded from the stream in turn are passed as
        a sole argument to the callable handler.
        :param handler: The callable handler to invoke with the decoded PDUs.
        :param stream: The byte stream to decode PDUs from.
        """
        index = 0
        while index < len(stream):
            if stream[index] != self._config["start_byte"]:
                raise Exception
            index += 1

            pdu_type = stream[index]
            if pdu_type in self._pdu:
                index += 1
                if self._pdu[pdu_type].get_length() > len(stream) - index:
                    raise Exception
                else:
                    self._pdu[pdu_type].decode(stream[index:index+self._pdu[pdu_type].get_length()])
                    handler(self._pdu[pdu_type].get_fields_values())
                    index += self._pdu[pdu_type].get_length()
            else:
                raise Exception

