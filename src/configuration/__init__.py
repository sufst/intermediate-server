"""
    Southampton University Formula Student Team Intermediate Server
    Copyright (C) 2021 Nathan Rowley-Smith

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
import xml.etree.ElementTree

__all__ = ["config"]


class ConfigurationManager:
    master_config = {}

    def init_config(self):
        self._init_config_socket_io()
        self._init_config_client()
        self._init_config_emulation()
        self._init_config_sensors()
        self._init_config_schema()

    def _build_dict_from_elem(self, elem, type_conversions):
        parsed = {}

        for entry in iter(elem):
            tag = entry.tag
            if len(entry) > 0:
                parsed[tag] = self._build_dict_from_elem(entry, type_conversions)
            else:
                text = entry.text
                if tag in type_conversions:
                    parsed[tag] = type_conversions[tag](text)
                else:
                    parsed[tag] = text
        return parsed

    def _init_config_socket_io(self):
        root = xml.etree.ElementTree.parse("socket_io.xml").getroot()

        parsed = self._build_dict_from_elem(root, {
            "interval": lambda x: float(x),
            "emulation": lambda x: x == "True",
            "retries": lambda x: int(x),
            "retry_interval": lambda x: int(x)
        })

        self.master_config["socket.io"] = parsed

    def _init_config_client(self):
        root = xml.etree.ElementTree.parse("client.xml").getroot()

        parsed = self._build_dict_from_elem(root, {
            "baud": lambda x: int(x),
            "port": lambda x: int(x)
        })

        self.master_config["client"] = parsed

    def _init_config_emulation(self):
        root = xml.etree.ElementTree.parse("emulation.xml").getroot()

        parsed = self._build_dict_from_elem(root, {
            "interval": lambda x: float(x)
        })

        self.master_config["emulation"] = parsed

    def _init_config_sensors(self):
        root = xml.etree.ElementTree.parse("sensors.xml").getroot()

        parsed = self._build_dict_from_elem(root, {
            "enable": lambda x: x == "True",
            "min": lambda x: int(x),
            "max": lambda x: int(x),
            "on_dash": lambda x: x == "True",
        })

        self.master_config["sensors"] = parsed

    def _init_config_schema(self):
        root = xml.etree.ElementTree.parse("schema.xml").getroot()

        parsed = self._build_dict_from_elem(root, {
            "start_byte": lambda x: int(x),
            "id": lambda x: int(x),
            "enable": lambda x: x == "True",
            "min": lambda x: int(x),
            "max": lambda x: int(x),
            "on_dash": lambda x: x == "True",
        })

        self.master_config["schema"] = parsed

    @property
    def socket_io(self):
        return self.master_config["socket.io"]

    @property
    def client(self):
        return self.master_config["client"]

    @property
    def emulation(self):
        return self.master_config["emulation"]

    @property
    def sensors(self):
        return self.master_config["sensors"]

    @property
    def schema(self):
        return self.master_config["schema"]


config = ConfigurationManager()
