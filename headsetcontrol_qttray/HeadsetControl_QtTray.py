"""
    Copyright 2022 Nikolai Eugen Sandvik

    This program is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by the Free Software Foundation,
    either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
    without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with this program.
    If not, see <https://www.gnu.org/licenses/>.
"""


import logging
import subprocess
import os

from PIL import Image, ImageFont, ImageDraw
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

LOG_LEVEL = logging.INFO


class Application:
    """
    Application class contains all the main logic of the application and is composite of the
    Headset class and tray class
    """

    def __init__(self):
        """
        Constructor setting up all required instances and logic of the application
        """
        self.interval = 120000  # default interval for checking battery 30 seconds
        self.app = QApplication([])
        self.headset = Headset()
        self.tray = Tray(self.headset)
        if not self.tray.isSystemTrayAvailable:
            logging.error("No Systemtray available to be used")
            exit(1)
        self.tray.set_menu(self)

        self.icon = None

        self.image_path = os.getenv("XDG_CACHE_HOME")
        if self.image_path is None:
            self.image_path = f"{os.getenv('HOME')}/."
            if self.image_path == "None/.":
                logging.error(
                    "Could not find environment variable HOME or XDG_CACHE_HOME"
                )
                exit(1)
        else:
            self.image_path += "/"


        self.setup()
        self.tray_update()

        self.timer = QTimer()
        self.timer.setInterval(self.interval)
        self.timer.timeout.connect(self.tray_update)
        self.timer.start()

    def setup(self):
        """
        setup sets any settings we need for the application
        :return:
        """
        self.app.setQuitOnLastWindowClosed(False)

    def create_icon(self):
        """
        Create the icon used by the tray based on the current status of the headset.
        Set icon instance attribute to the newly created icon.
        :return:
        """
        if not self.headset.connected:
            icon = ""
            font_size = 60
            pos = (9, -9)
            color = (255, 0, 0, 255)
        elif self.headset.charge == -1:
            icon = ""
            font_size = 70
            pos = (5, -15)
            color = (0, 255, 150, 255)
        else:
            icon = ""
            font_size = 60
            pos = (9, -9)
            if self.headset.charge > 80:
                color = (0, 255, 0, 255)
            elif self.headset.charge > 40:
                color = (234, 255, 0, 255)
            elif self.headset.charge > 20:
                color = (255, 90, 0, 255)
            else:
                color = (255, 0, 0, 255)

        font = ImageFont.truetype(
            f"{os.path.abspath(os.path.dirname(__file__))}/DroidNerd.otf", font_size
        )
        image = Image.new("RGBA", (50, 50), color=(0, 0, 0, 0))
        image_draw = ImageDraw.Draw(image)
        image_draw.text(pos, icon, fill=color, font=font)
        image.save(f"{self.image_path}headsetcontrol_tray_icon.png")
        self.icon = QIcon(f"{self.image_path}headsetcontrol_tray_icon.png")

    def check_status(self):
        """
        Checks the status of the headset by running headsetcontrol with the b argument.
        Will check capabilities if none are set.
        :return:
        """
        if self.headset.capabilities is None:
            self.headset.run_command(["--capabilities", "-c"])
            if self.headset.capabilities is not None:
                self.tray.set_menu(self)
                pass

        self.headset.run_command(["-b", "-c"])

    def tray_update(self):
        """
        Checks the status of headset, creates new icon and set the new icon to represent the current state of the headset
        :return:
        """
        logging.info("Updating tray icon")
        self.check_status()
        self.create_icon()
        self.tray.battery.setText(self.headset.charge_status())
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)


class Tray(QSystemTrayIcon):
    """
    Subclass of QSystemTrayIcon
    Extends it to set up the menu used by the tray icon.
    """

    def __init__(self, headset):
        super().__init__()

        self.main_menu = QMenu()

        # Quit
        self.quit = QAction("Quit")
        # light
        self.light_off = QAction("Turn Light Off")
        self.light_on = QAction("Turn Light On")
        # Force refresh
        self.refresh = QAction("Refresh battery state")
        self.battery = QAction(headset.charge_status())
        # Sidetone
        self.sidetone_menu = QMenu("Sidetone", parent=self.main_menu)
        self.sidetone_off = QAction("Off")
        self.sidetone_low = QAction("Low")
        self.sidetone_med = QAction("Medium")
        self.sidetone_high = QAction("High")
        self.sidetone_max = QAction("Max")


    def set_menu(self, application):
        """
        Adds the menu options that are supported by the connected headset.
        :param application: The application class running the tray
        :return:
        """

        if (application.headset.capabilities is not None):
            if ("l" in application.headset.capabilities): # Capability controlling lights
                self.light_on.triggered.connect(application.headset.turn_ligt_on)
                self.light_off.triggered.connect(application.headset.turn_light_off)

                self.main_menu.addAction(self.light_on)
                self.main_menu.addAction(self.light_off)

            if ("b" in application.headset.capabilities): # Capability checking battery
                self.refresh.triggered.connect(application.tray_update)
                self.main_menu.addAction(self.refresh)
                self.main_menu.addAction(self.battery)

            if ("s" in application.headset.capabilities): # Capability Sidetone
                self.sidetone_off.triggered.connect(application.headset.sidetone_off)
                self.sidetone_low.triggered.connect(application.headset.sidetone_low)
                self.sidetone_med.triggered.connect(application.headset.sidetone_med)
                self.sidetone_high.triggered.connect(application.headset.sidetone_high)
                self.sidetone_max.triggered.connect(application.headset.sidetone_max)

                self.sidetone_menu.addAction(self.sidetone_max)
                self.sidetone_menu.addAction(self.sidetone_high)
                self.sidetone_menu.addAction(self.sidetone_med)
                self.sidetone_menu.addAction(self.sidetone_low)
                self.sidetone_menu.addAction(self.sidetone_off) 
                self.main_menu.addMenu(self.sidetone_menu)

        self.quit.triggered.connect(application.app.quit)
        self.main_menu.addAction(self.quit)

        # Set the menu
        self.setContextMenu(self.main_menu)


class Headset:
    """
    Represents the headset managed by HeadsetControl
    """

    def __init__(self):
        """
        Constructor  for the headset class
        Includes all attributes needed to check the state of the headset.
        """
        self.capabilities = None
        self.connected = False
        self.charge = 0

        self.run_command(["--capabilities", "-c"])
        if self.connected:
            self.run_command(["-b", "-c"])

    def turn_ligt_on(self):
        """
        Runs command to turn light on for headset that support.
        """
        self.run_command(["-l", "1", "-c"])

    def turn_light_off(self):
        """
        Runs command to turn light Off for headset that support.
        """
        self.run_command(["-l", "0", "-c"])

    def sidetone_off(self):
        """
        Runs command to turn off sidetone
        """
        self.run_command(["-s", "0", "-c"])
    
    def sidetone_low(self):
        """
        Runs command to set sidetone to 32
        """
        self.run_command(["-s", "32", "-c"])

    def sidetone_med(self):
        """
        Runs command to set sidetone to 64
        """
        self.run_command(["-s", "64", "-c"])

    def sidetone_high(self):
        """
        Runs command to set sidetone to 96
        """
        self.run_command(["-s", "96", "-c"])

    def sidetone_max(self):
        """
        Runs command to set sidetone to 128
        """
        self.run_command(["-s", "128", "-c"])


    def run_command(self, argument_list):
        """
        Runs headsetcontrol application with the specified argument.
        :param argument_list: list with string arguments. Each argument seperated
        :return:
        """

        if not isinstance(argument_list, list) and all(
            isinstance(elem, str) for elem in argument_list
        ):
            logging.debug(
                "run_headsetcontrol argument not list or list contains something that is not a string"
            )
            return

        if (self.capabilities is None and argument_list[0] != "--capabilities") or (
            self.capabilities is not None
            and argument_list[0].replace("-", "") not in self.capabilities
        ):
            logging.warning(
                f"{argument_list[0]} not in capabilities {self.capabilities}"
            )
            return

        process = subprocess.run(
            args=["headsetcontrol", *argument_list], capture_output=True
        )

        if process.returncode != 0:
            self.connected = False
            logging.debug(
                f"run_headsetcontrol return code {process.returncode} : {process.stderr}"
            )
            return

        if argument_list[0] == "-b":
            output = process.stdout.decode("UTF-8")
            if output == "-2":
                self.connected = False
            elif output == "-1":
                self.charge = -1
                self.connected = True
            else:
                self.charge = int(output)
                self.connected = True
        elif argument_list[0] == "--capabilities":
            self.capabilities = process.stdout.decode("UTF-8")
        # Other commands dont give output so we just continue hoping it worked
        # if we dont't get a error code.

    def charge_status(self):
        """
        returns a string representation of the current charge status.
        :return:
        """
        if self.charge == -2:
            return "Disconnected"
        elif self.charge == -1:
            return "Charging"
        else:
            return f"{self.charge}%"


def main():
    # TODO check that headsetcontrol is actually installed
    # setup logging
    logging.basicConfig(
        level=LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    app = Application()
    app.app.exec()


if __name__ == "__main__":
    main()
