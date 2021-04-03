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
import struct


class PDU:
    def __init__(self, name: str, structure: dict):
        """
        Sub class to encapsulate a PDU.

        Each PDU defined within the schema will each have a corresponding instance of this class
        associated with it. The class is used as a helper for decoding and parsing of PDUs from streams.
        :param name: The name of the PDU.
        :param structure: The dictionary containing the structure of the PDU.
        """
        self.name = name
        self.length = 0
        self._struct = structure

        self._parse_pdu()

    def _parse_pdu(self):
        self._fields_names = []
        self.fields = {}

        self._struct_format = "<"

        c_type_lengths = {"c": 1, "b": 1, "B": 1, "?": 1, "h": 2, "H": 2, "i": 4, "I": 4,
                          "l": 4, "L": 4, "f": 4, "d": 8, "q": 8, "Q": 8}

        for field, conf in self._struct.items():
            for conf_name, conf_value in conf.items():
                if conf_name == "c_type":
                    self._fields_names.extend([field])
                    self.length += c_type_lengths[conf_value]
                    self._struct_format += conf_value

        # Remove the valid_bitfield field.
        self._fields_names = self._fields_names[1:]

    def decode(self, bytes_in: bytes) -> None:
        """
        Decode the PDU from the bytes object.
        :param bytes_in: Bytes to decode the PDU from.
        """
        values = iter(struct.unpack(self._struct_format, bytes_in))

        # The first value should be the valid bitfield.
        valid_bitfield = next(values)

        # Create an array of valid fields in the PDU
        valid_fields = []
        for i in range(0, len(self._fields_names)):
            if (valid_bitfield >> i) & 1:
                valid_fields.extend([self._fields_names[i]])

        for field in self._fields_names:
            if field in valid_fields:
                self.fields[field] = next(values)
            else:
                next(values)
