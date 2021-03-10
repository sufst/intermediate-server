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

import server

_SW_VERSION = "0.9.0"

if __name__ == '__main__':
    print(f"Intermediate Server build {_SW_VERSION} Copyright (C) 2021 Nathan Rowley-Smith\n" +
          "This program comes with ABSOLUTELY NO WARRANTY;\n" +
          "This is free software, and you are welcome to redistribute it")

    with server.Server() as server:
        server.serve_forever()
