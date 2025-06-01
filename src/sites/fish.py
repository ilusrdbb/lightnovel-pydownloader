from aiohttp import ClientSession

from src.utils.config import read_config


class Fish():

    def __init__(self, session: ClientSession):
        super().__init__(session)
        self.site: str = "fish"
        self.domain: str = read_config("domain")["fish"]