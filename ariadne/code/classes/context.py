"""Module for defining the context class of the application"""
import aioredis
import pytest
from starlette.requests import Request
from code.init_lightning import init_lightning, lnd_tests
from code.helpers.mixins import LoggerMixin
from code.classes.user import User
from code.classes.bitcoin import BitcoinClient


class Context(LoggerMixin):
    """class for passing context values"""

    def __init__(self, config: dict):
        LoggerMixin().__init__()
        self.logger.info(config)
        self._config = config
        self.req = None #populated on each server request
        self.redis = None
        self.lnd = init_lightning(
            host=config['lnd']['grpc'],
            network=config['network']
        )
        self.id_pubkey = None
        self.bitcoind = BitcoinClient(config['bitcoind'])
        self.logger.warning('initialized context')
        # DEFINE cached variables in global context
    
    def __call__(self, req: Request):
        self.req = req
        return self

    async def async_init(self):
        """async init redis db. call before app startup"""
        self.logger.warning('instantiating redis')
        self.redis = await aioredis.create_redis_pool(self._config['redis']['host'])
        self.logger.warning(self.redis)


    async def destroy(self):
        """Destroy close necessary connections gracefully"""
        self.logger.info('Destroying redis instance')
        self.redis.close()
        await self.redis.wait_closed()

    # TODO smoke tests for connected containers
    async def smoke_tests(self):
        self.id_pubkey = await lnd_tests()