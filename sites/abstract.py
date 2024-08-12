from abc import abstractmethod
from asyncio import Semaphore

from aiohttp import ClientSession

from models.cookie import Cookie


class Site(object):
    cookie: Cookie
    session: ClientSession
    header: dict
    site: str
    thread: Semaphore

    async def run(self):
        await self.login()
        await self.get_books()

    @abstractmethod
    async def login(self):
        pass

    @abstractmethod
    async def valid_cookie(self) -> bool:
        pass

    @abstractmethod
    async def get_cookie(self):
        pass

    @abstractmethod
    async def get_books(self):
        pass
