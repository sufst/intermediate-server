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

import logging
import os
import datetime

__formatter = logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s]: %(message)s")
__start_time_fmt = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")


def get_logger(name: str, verbose: str) -> logging.Logger:
    """
    Get a logger instance and create the corresponding file logs.
    :param name:    The name to give the logger.
    :param verbose: The verbose level of the logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(verbose))

    console = logging.StreamHandler()
    console.setLevel(logging.getLevelName(verbose))
    console.setFormatter(__formatter)
    logger.addHandler(console)

    log_file = f"logs/{__start_time_fmt}/{name}"

    try:
        if not os.path.exists(f"{log_file}"):
            os.makedirs(log_file)
    except OSError as err:
        print(f"Unable to create log file {log_file}: {repr(err)}")
    else:
        file = logging.FileHandler(f"{log_file}.log", mode='w+')
        file.setLevel(logging.DEBUG)
        file.setFormatter(__formatter)
        logger.addHandler(file)

    return logger
