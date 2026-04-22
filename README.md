# RommDrop

RommDrop is a dead simple ROM downloader for RetroBat and EmulationStation. It provides a lightweight, controller-driven interface to browse and download ROMs from a RomM server directly into the appropriate local platform directories. RommDrop is designed to be self-contained. It uses a portable Python interpreter within its own directory structure, ensuring that no system-wide Python installation is required for the end user.


***Features***

Automatically detects and lists platforms available on the RomM server, loads this on launch

Includes a search function an on-screen keyboard, unfortunately real keyboard access is not currently supported..

Detects the RetroBat root directory and places downloaded files in the correct subfolders based on platform slugs. "It Just Works."

U.I Built with Pygame for easy borderless fullscreen and native controller input.


***Setup and Installation***

Place the "roms" folder found in RommDrop_current in your RetroBat Base Folder, something like C:/Games/RetroBat

The application requires a config.json file located in the .RommDrop directory. Edit this file with your server details:

JSON
{
    "romm_url": "https:// or http://yourserver:6969",
    "username": "YourUsername",
    "password": "YourPassword"
}


***Navigation***

The interface is designed for 100% controller navigation. There is unfortunately no way to navigate the app with a mouse and keyboard currently.

D-Pad: Navigate menus and on-screen keyboard.

A Button: Select platform, download game, or type character.

B Button: Universal back button to return to the system list.

LB / RB: Page navigation (scroll through lists 10 items at a time).

Start + Select: Exit the application and return to the frontend.

Y Button: Instant jump to Search Mode.

X Button: Backspace (delete last character) while typing.
