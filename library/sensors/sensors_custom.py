# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# This file allows to add custom data source as sensors and display them in System Monitor themes
# There is no limitation on how much custom data source classes can be added to this file
# See CustomDataExample theme for the theme implementation part

import math
import platform
from abc import ABC, abstractmethod
from typing import List


# Custom data classes must be implemented in this file, inherit the CustomDataSource and implement its 2 methods
class CustomDataSource(ABC):
    @abstractmethod
    def as_numeric(self) -> float:
        # Numeric value will be used for graph and radial progress bars
        # If there is no numeric value, keep this function empty
        pass

    @abstractmethod
    def as_string(self) -> str:
        # Text value will be used for text display and radial progress bar inner text
        # Numeric value can be formatted here to be displayed as expected
        # It is also possible to return a text unrelated to the numeric value
        # If this function is empty, the numeric value will be used as string without formatting
        pass

    @abstractmethod
    def last_values(self) -> List[float]:
        # List of last numeric values will be used for plot graph
        # If you do not want to draw a line graph or if your custom data has no numeric values, keep this function empty
        pass


# Example for a custom data class that has numeric and text values
class ExampleCustomNumericData(CustomDataSource):
    # This list is used to store the last 10 values to display a line graph
    last_val = [math.nan] * 10  # By default, it is filed with math.nan values to indicate there is no data stored

    def as_numeric(self) -> float:
        # Numeric value will be used for graph and radial progress bars
        # Here a Python function from another module can be called to get data
        # Example: self.value = my_module.get_rgb_led_brightness() / audio.system_volume() ...
        self.value = 75.845

        # Store the value to the history list that will be used for line graph
        self.last_val.append(self.value)
        # Also remove the oldest value from history list
        self.last_val.pop(0)

        return self.value

    def as_string(self) -> str:
        # Text value will be used for text display and radial progress bar inner text.
        # Numeric value can be formatted here to be displayed as expected
        # It is also possible to return a text unrelated to the numeric value
        # If this function is empty, the numeric value will be used as string without formatting
        # Example here: format numeric value: add unit as a suffix, and keep 1 digit decimal precision
        return f'{self.value:>5.1f}%'
        # Important note! If your numeric value can vary in size, be sure to display it with a default size.
        # E.g. if your value can range from 0 to 9999, you need to display it with at least 4 characters every time.
        # --> return f'{self.as_numeric():>4}%'
        # Otherwise, part of the previous value can stay displayed ("ghosting") after a refresh

    def last_values(self) -> List[float]:
        # List of last numeric values will be used for plot graph
        return self.last_val


# Example for a custom data class that only has text values
class ExampleCustomTextOnlyData(CustomDataSource):
    def as_numeric(self) -> float:
        # If there is no numeric value, keep this function empty
        pass

    def as_string(self) -> str:
        # If a custom data class only has text values, it won't be possible to display graph or radial bars
        return "Python: " + platform.python_version()

    def last_values(self) -> List[float]:
        # If a custom data class only has text values, it won't be possible to display line graph
        pass
# ============================================================
# Proxmox VE - lightweight custom sensors
# ============================================================

import json
import os
import socket
import subprocess
import time


# ------------------------------------------------------------
# Cache
# ------------------------------------------------------------

_PVE_GUEST_CACHE = {
    "timestamp": 0,
    "data": None,
}

_PVE_GUEST_CACHE_TTL = 20

_PVE_SERVER_INFO = None


# ------------------------------------------------------------
# Base class
# ------------------------------------------------------------

class ProxmoxTextDataSource(CustomDataSource):
    """
    Base para sensores textuais do Proxmox.

    Esses sensores não utilizam gráfico/histórico,
    portanto não precisam fornecer valor numérico.
    """

    def as_numeric(self):
        pass

    def last_values(self):
        pass


# ------------------------------------------------------------
# Guests
# ------------------------------------------------------------

def _get_proxmox_guests():
    """
    Obtém todas as VMs + LXCs usando UMA única consulta pvesh.

    Endpoint:
        /cluster/resources --type vm

    O resultado fica em cache por 20 segundos.
    """

    global _PVE_GUEST_CACHE

    now = time.monotonic()

    cached_data = _PVE_GUEST_CACHE["data"]
    cached_time = _PVE_GUEST_CACHE["timestamp"]

    if (
        cached_data is not None
        and now - cached_time < _PVE_GUEST_CACHE_TTL
    ):
        return cached_data

    try:
        result = subprocess.run(
            [
                "/usr/bin/pvesh",
                "get",
                "/cluster/resources",
                "--type",
                "vm",
                "--output-format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        data = json.loads(result.stdout)

        if not isinstance(data, list):
            data = []

        _PVE_GUEST_CACHE = {
            "timestamp": now,
            "data": data,
        }

        return data

    except Exception:
        # Em caso de falha transitória, reutiliza
        # o último resultado válido.
        if cached_data is not None:
            return cached_data

        return []


def _get_local_guests():
    """
    Filtra somente guests pertencentes ao node atual.
    """

    node = socket.gethostname()

    return [
        guest
        for guest in _get_proxmox_guests()
        if guest.get("node") == node
    ]


# ------------------------------------------------------------
# VM
# ------------------------------------------------------------

class ProxmoxVMs(ProxmoxTextDataSource):

    def as_string(self):
        guests = _get_local_guests()

        vms = [
            guest
            for guest in guests
            if guest.get("type") == "qemu"
        ]

        total = len(vms)

        running = sum(
            1
            for vm in vms
            if vm.get("status") == "running"
        )

        return f"{running}/{total}"


# ------------------------------------------------------------
# LXC
# ------------------------------------------------------------

class ProxmoxCTs(ProxmoxTextDataSource):

    def as_string(self):
        guests = _get_local_guests()

        containers = [
            guest
            for guest in guests
            if guest.get("type") == "lxc"
        ]

        total = len(containers)

        running = sum(
            1
            for ct in containers
            if ct.get("status") == "running"
        )

        return f"{running}/{total}"


# ------------------------------------------------------------
# Uptime
# ------------------------------------------------------------

class ProxmoxUptime(ProxmoxTextDataSource):

    def as_string(self):
        try:
            with open(
                "/proc/uptime",
                "r",
                encoding="utf-8"
            ) as f:
                seconds = int(
                    float(f.read().split()[0])
                )

            days = seconds // 86400
            hours = (seconds % 86400) // 3600

            if days > 0:
                return f"{days}d {hours}h"

            minutes = (seconds % 3600) // 60

            return f"{hours}h {minutes}m"

        except Exception:
            return "N/A"


# ------------------------------------------------------------
# Load average
# ------------------------------------------------------------

class ProxmoxLoad(ProxmoxTextDataSource):

    def as_string(self):
        try:
            return f"{os.getloadavg()[0]:.2f}"

        except Exception:
            return "N/A"


# ------------------------------------------------------------
# Hostname + PVE
# ------------------------------------------------------------

class ProxmoxServer(ProxmoxTextDataSource):

    def as_string(self):
        global _PVE_SERVER_INFO

        # Hostname e versão não mudam durante a execução.
        # Consulta apenas uma vez.
        if _PVE_SERVER_INFO is not None:
            return _PVE_SERVER_INFO

        hostname = socket.gethostname()

        try:
            result = subprocess.run(
                ["/usr/bin/pveversion"],
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            )

            raw_version = result.stdout.strip()

            # pve-manager/9.2.18/xxxxxxxx
            if "/" in raw_version:
                version = raw_version.split("/")[1]
            else:
                version = raw_version

            _PVE_SERVER_INFO = (
                f"{hostname}  PVE {version}"
            )

        except Exception:
            _PVE_SERVER_INFO = hostname

        return _PVE_SERVER_INFO

from datetime import datetime


class ProxmoxDate(ProxmoxTextDataSource):

    def as_string(self):
        return datetime.now().strftime("%d/%m/%Y")


class ProxmoxTime(ProxmoxTextDataSource):

    def as_string(self):
        return datetime.now().strftime("%H:%M")