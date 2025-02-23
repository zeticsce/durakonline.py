import json
from msgspec.json import decode
from .utils import objects
from typing import List, Union


class Game:
    def __init__(self, client):
        self.client = client

    def create(self, bet: int = 100, password: str = "", players: int = 2,
        deck: int = 24, fast: bool = False, sw: bool = True,
        nb: bool = True, ch: bool = False, dr: bool = True) -> objects.Game:
        self.client.send_server(
            {
                "command": "create",
                "bet": bet,
                "password": password,
                "fast": fast,
                "sw": sw,
                "nb": nb,
                "ch": ch,
                "players": players,
                "deck": deck,
                "dr": dr
            }
        )

        data = self.client._get_data("game")
        if data["command"] == 'err':
            raise objects.Err(data)
        return decode(json.dumps(data), type=objects.Game)

    def join(self, password: Union[str, None], game_id: int) -> objects.Game:
        payload = {
            'command': 'join',
            'id': game_id
        }

        if password is not None:
            payload['password'] = password

        self.client.send_server(payload)
        data = self.client._get_data('game')
        if data['command'] in ['err', 'alert']:
            raise objects.Err(data)
        return decode(json.dumps(data), type=objects.Game)

    def invite(self, user_id: int):
        self.client.send_server(
            {
                "command": "invite_to_game",
                "user_id": user_id
            }
        )

    def rejoin(self, position: int, game_id: int) -> objects.Game:
        self.client.send_server(
            {
                "command": "rejoin",
                "p": position,
                "id": game_id
            }
        )
        data = self.client._get_data("game")
        if data["command"] == 'err':
            raise objects.Err(data)
        return decode(json.dumps(data), type=objects.Game)

    def leave(self, game_id: Union[int, None] = None) -> dict:
        data = {
            "command": "leave",
        }
        if game_id:
            data["id"] = game_id
        self.client.send_server(data)
        return self.client._get_data("uu")

    def publish(self) -> None:
        return self.client.send_server(
            {
                "command": "game_publish"
            }
        )

    def send_smile(self, smile_id: int = 16) -> None:
        self.client.send_server(
            {
                "command": "smile",
                "id": smile_id
            }
        )

    def ready(self) -> None:
        self.client.send_server(
            {
                "command": "ready"
            }
        )

    def surrender(self) -> None:
        self.client.send_server(
            {
                "command": "surrender"
            }
        )

    def player_swap(self, position: int) -> None:
        self.client.send_server(
            {
                "command": "player_swap",
                "id": position
            }
        )

    def turn(self, card: str) -> None:
        self.client.send_server(
            {
                "command": "t",
                "c": card
            }
        )

    def feed(self, card: str) -> None:
        self.client.send_server(
            {
                'command': 'f',
                'c': card,
            }
        )

    def take(self) -> None:
        self.client.send_server(
            {
                "command": "take"
            }
        )

    def do_pass(self) -> None:
        self.client.send_server(
            {
                "command": "pass"
            }
        )
    
    def done(self) -> None:
        self.client.send_server(
            {
                'command': 'done'
            }
        )
    
    def beat(self, card: str, card_to_beat: str) -> None:
        self.client.send_server(
            {
                'command': 'b',
                'c': card_to_beat,
                'b': card,
            }
        )

    def report_trick(self, card: str, card_beaten: str) -> None:
        self.client.send_server(
            {
                'command': 'chb',
                'c': card_beaten,
                'b': card,
            }
        )

    def forward_card(self, card: str) -> None:
        self.client.send_server(
            {
                'command': 's',
                'c': card
            }
        )

    def get_hands(self) -> None:
        self.client.send_server(
            {
                'command': 'get_hands'
            }
        )

    def get_table(self) -> None:
        self.client.send_server(
            {
                'command': 'get_table'
            }
        )

    def lookup_start(self, betMin: int = 100, pr: bool = False, betMax: int = 2500,
        fast: bool = True, sw: bool = True, nb: list = [False, True], ch: bool = False,
        players: list = [2, 3, 4, 5, 6], deck: list = [24, 36, 52], dr: bool = True) -> List[objects.GameInList]:
        self.client.send_server(
            {
                "command": "lookup_start",
                "betMin": betMin,
                "pr": [pr, False],
                "betMax": betMax,
                "fast": [fast],
                "sw": [sw],
                "nb": nb,
                "ch": [ch],
                "players": players,
                "deck": deck,
                "dr": [dr],
                "status": "open"
            }
        )
        response = self.client._get_data("gl")
        games: List[objects.GameInList] = []
        for game in response.get("g", []):
            games.append(decode(json.dumps(game), type=objects.GameInList))
        return games

    def lookup_stop(self) -> None:
        self.client.send_server(
            {
                "command": "lookup_stop"
            }
        )
