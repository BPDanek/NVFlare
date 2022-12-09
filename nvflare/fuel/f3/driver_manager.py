#  Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from typing import List, Union
from nvflare.fuel.utils.class_utils import get_class
from .constants import DriverUse, DriverRequirementKey, Visibility
from .driver import DriverSpec


class DriverResource:

    def __init__(
            self,
            driver_name: str,
            resources: dict = None
    ):
        """

        Args:
            driver_name: name of the driver class
            resources: additional info to assist creating new listeners or connectors. This info could include
            - port numbers
            - base url
        """
        self.driver_name = driver_name
        self.resources = resources


class DriverManager:

    """
    Manages creation of drivers (listeners and connectors).

    Each Driver Class must implement class methods for:
    - get_name()
    - set_properties() to set additional properties
    - new_listener() to generate a listener object based on connection requirements
    - new_connector() to generate a connector object based on connection properties
    """

    DRIVERS = {
        "http": "nvflare.fuel.f3.drivers.http.HTTPDriver",
        "ipc": "nvflare.fuel.f3.drivers.ipc.IPCDriver",
    }

    def __init__(self):
        self.driver_classes = {}  # name => class

        # load default driver classes
        for name, class_path in self.DRIVERS.items():
            self.driver_classes[name] = get_class(class_path)

        self.ext_drivers = ["http"]
        self.int_drivers = ["http"]
        self.int_driver_resources = {
            "http": {
                "url": "http://localhost",
                "ports": [(24000, 25000)]  # select a port randomly in the range
            }
        }
        self.adhoc_ext_driver_resources = {}

    def add_resources(self, resources: List[DriverResource]):
        for r in resources:
            self.adhoc_ext_driver_resources[r.driver_name] = r.resources

    def _get_driver(self, active: bool, requirements):
        use = requirements.get(DriverRequirementKey.USE, DriverUse.BACKBONE)
        vis = requirements.get(DriverRequirementKey.VISIBILITY, Visibility.EXTERNAL)
        resource_config = {}
        if use == DriverUse.BACKBONE:
            if vis == Visibility.EXTERNAL:
                drivers = self.ext_drivers
            else:
                drivers = self.int_drivers
                resource_config = self.int_driver_resources
        else:
            drivers = self.ext_drivers
            resource_config = self.adhoc_ext_driver_resources

        for name in drivers:
            clazz = self.driver_classes.get(name)
            resources = resource_config.get(name)
            if clazz:
                try:
                    driver = clazz(
                        active=active,
                        conn_requirements=requirements,
                        resources=resources
                    )
                    return driver
                except:
                    pass
        return None

    def get_listener(
            self,
            requirements: dict) -> Union[None, DriverSpec]:
        """
        Try to get a listener that can satisfy the requirements specified in conn_requirements.
        The conn_requirements could specify very precise requirements like secure or not, scheme, domain, port;
        The conn_requirements could also only specify general requirements like connection type (ext or internal)

        Args:
            requirements: required connection properties

        Returns: tuple of: dict of conn props, a listener or None.
        The returned conn props dict must contain sufficient info for others to make a connection:
        secure mode or not, scheme (http, tcp, ipc, etc), domain name, port number, etc.

        We simply try each driver class to get the required listener, until we get a listener.
        """
        return self._get_driver(
            active=False,
            requirements=requirements,
        )

    def get_connector(
            self,
            requirements: dict) -> Union[None, DriverSpec]:
        """
        Try to get a Connector for the specified conn_requirements, which contains info for making connection.

        Args:
            requirements: dict that contains info for making a connection

        Returns: a connector or None

        We simply try each driver class to get a connector.
        """
        return self._get_driver(
            active=True,
            requirements=requirements,
        )