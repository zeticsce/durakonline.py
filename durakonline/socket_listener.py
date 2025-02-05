import atexit
import socket
import socks
import json
import requests
import threading
import random
from queue import Queue
from durakonline.utils import Server
import contextlib
from typing import Callable, TYPE_CHECKING, Any
import logging


if TYPE_CHECKING:
    from .durakonline import Client


logger = logging.getLogger(__name__)


class SocketListener:
    def __init__(self: 'Client', client, proxy: str = ""):
        self.client = client
        self.proxy = proxy
        self.alive = False
        self.api_url: str = "http://static.rstgames.com/durak/"
        self.socket: socks.socksocket = None
        self.receive: Queue = Queue()
        self.handlers: dict[str, list[Callable[[dict], ...]]] = {}
        self.thread: threading.Thread = None
        self.reconnection_data = {'interval': 3, 'limit': 5, 'lock': threading.Lock(), 'is_reconnected': False, 'terminated': False}

    def create_connection(self: 'Client', server_id: Server = None, ip: str = None, port: int = None):
        if not ip:
            servers = self.get_servers()["user"]
            server = servers[server_id] if server_id else list(random.choice(list(servers.items())))[1]
            ip = server["host"]
            port = server["port"]
        if self.proxy:
            proxy_login, proxy_password, proxy_ip, proxy_port = self.proxy.replace("@", ":").split(":")

            socks.set_default_proxy(socks.SOCKS5, proxy_ip, int(proxy_port), username=proxy_login, password=proxy_password)
            socket.socket = socks.socksocket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.settimeout(10)
            self.socket.connect((ip, port))
        except Exception as e:
            if "error" in self.handlers:
                self.handlers["error"](e)
            return
        
        if self.alive and self.thread:
            self.alive = False
            self.thread.join()

        self.alive = True
        self.thread = threading.Thread(target=self.receive_messages)
        self.thread.start()

    def send_server(self: 'Client', data: dict):
        if not self.socket:
            raise ValueError('Socket not created')
        try:
            with self.reconnection_data['lock']:
                self.socket.send(
                    (
                        data.pop('command') + json.dumps(data, separators=(',', ':')
                    ).replace("{}", '')+'\n').encode()
                )
        except (ConnectionResetError, BrokenPipeError) as e:
            if self.reconnection_data['terminated']:
                raise e
            
            self.reconnect(e)
            return self.send_server(data=data)
        except Exception as e:
            logger.exception('')
            if "error" in self.handlers:
                self.handlers["error"](e)
    
    def reconnect(self: 'Client') -> bool:
        with self.reconnection_data['lock']:
            if self.reconnection_data['is_reconnected']:
                return False
            
            self.socket.close()

            for count_reconn in range(limit := self.reconnection_data['limit']):
                try:
                    self.create_connection()
                except Exception:
                    logger.exception(
                        f'Error while reconnecting to server ({count_reconn + 1} / {limit} attempts)'
                    )
                else:
                    self.reconnection_data['is_reconnected'] = True
                    logger.warning(
                        f'Successfully reconnected to server for {count_reconn + 1} attempts'
                    )
                    return True
            else:
                logger.critical('Connection loss, out of attempts')

    def get_servers(self: 'Client') -> dict:
        try:
            response = requests.get(f"{self.api_url}servers.json").json()
        except Exception as e:
            if "error" in self.handlers:
                self.handlers["error"](e)
            return
        return response

    def event(self: 'Client', command: str = "all"):
        def register_handler(handler):
            self.handlers.setdefault('command', []).append(handler)
            return handler

        return register_handler

    def register_handler(self: 'Client', command: str = "all", handler: Callable[[dict], Any] = ...):
        assert callable(handler)
        self.handlers.setdefault(command, []).append(handler)
        
    def error(self: 'Client'):
        def register_handler(handler: Callable[[Exception], ...]):
            self.handlers["error"] = handler
            return handler

        return register_handler

    def receive_messages(self: 'Client'):
        self.logger.debug(f"{self.tag}: Start listener")
        _ = [x() for x in self.handlers.get('init', [])]

        while self.alive:
            buffer = bytes()
            while self.alive:
                try:
                    r = self.socket.recv(4096)
                except Exception as e:
                    if not self.alive:
                        break
                    if "error" in self.handlers:
                        self.handlers["error"](e)

                    if self.reconnection_data['terminated']:
                        self.alive = False
                        return
                    
                    self.reconnect()
                    continue
                
                buffer = buffer + r
                read = len(r)
                if read != -1:
                    if read < 2:
                        continue
                    try:
                        d = buffer.decode()
                    except UnicodeDecodeError:
                        continue
                    if d.endswith('\n'):
                        buffer = bytes()
                        for message_str in d.strip().split('\n'):
                            message_str = message_str[0:-1]
                            pos = message_str.find('{')
                            command = message_str[:pos]
                            try:
                                message = json.loads(message_str[pos:]+"}")
                            except Exception:
                                continue
                            message['command'] = command
                            self.logger.debug(f"{self.tag}: {message}")
                            for handler_command in self.handlers:
                                if handler_command in ["all", command]:
                                    for handler in self.handlers[handler_command]:
                                        try:
                                            handler(message)
                                        except Exception:
                                            self.logger.exception(f'Exc in {handler!r}:\n')

                            self.receive.put(message)
                    else:
                        continue
                else:
                    if self.reconnection_data['terminated']:
                        self.socket.close()
                        return
                    
                    self.reconnect()
                    continue

            _ = [x() for x in self.handlers.get('shutdown', [])]

    def listen(self: 'Client'):
        try:
            response = self.receive.get(timeout=15)
        except Exception:
            logger.exception('Error while receive response')
            response = {'command': 'err'}

        return response

    def _get_data(self: 'Client', command: str):
        data = self.listen()
        while True:
            if data["command"] in [command, "err", "alert"]:
                return data
            data = self.listen()
    
    def shutdown(self: 'Client') -> None:
        if self.alive:
            self.alive = False

        if self.socket is not None:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None

        if self.thread is not None:
            self.thread.join()
            self.thread = None
        
        with contextlib.suppress(AttributeError):
            if not self.receive.is_shutdown:
                self.receive.shutdown()

    def __del__(self: 'Client') -> None:
        atexit.unregister(self.shutdown)
