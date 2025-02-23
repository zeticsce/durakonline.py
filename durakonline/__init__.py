__title__ = "durakonline.py"
__author__ = "Zakovskiy"
__license__ = "MIT"
__copyright__ = "Copyright 2021-2025 Zakovskiy"
__version__ = "3.7.1"

from .durakonline import Client
from .authorization import Authorization
from .game import Game
from .friend import Friend
from .socket_listener import SocketListener

from .utils import objects
from .utils import enums

__all__ = (
    'Client',
    'Authorization',
    'Game',
    'Friend',
    'SocketListener',
    'objects',
    'enums'
)

from requests import get
from json import loads

__newest__ = loads(get("https://pypi.python.org/pypi/durakonline.py/json").text)["info"]["version"]

if __version__ != __newest__:
    exit(f"New version of {__title__} available: {__newest__} (Using {__version__})")
