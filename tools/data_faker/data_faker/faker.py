import datetime
import logging
import random
from typing import Optional

from data_faker.actions import ActionWriter
from data_faker.fake_binance import FakeBinance
from data_faker.fake_kraken import FakeKraken
from data_faker.mock_apis.api import APIServer, RestAPI
from faker import Faker

from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.factories import make_random_b64bytes

logger = logging.getLogger(__name__)


class DataFaker(object):

    def __init__(self, args):
        args.logfile = 'data_faker.log'
        self.rotki = Rotkehlchen(args)

        random_seed = datetime.datetime.now()
        logger.info(f'Random seed used: {random_seed}')
        random.seed(random_seed)
        self.faker = Faker()

        self.create_new_user(args.user_name, args.user_password)

        # Start the fake exchanges API for the duration of the fake
        # history creation. We need it up so that we can emulate responses
        # from the exchanges
        self.fake_kraken = FakeKraken()
        self.fake_binance = FakeBinance()
        mock_api = RestAPI(fake_kraken=self.fake_kraken, fake_binance=self.fake_binance)
        self.mock_server = APIServer(rest_api=mock_api)
        self.mock_server.start()

        self.rotki.setup_exchange(
            name='kraken',
            api_key=str(make_random_b64bytes(128)),
            api_secret=str(make_random_b64bytes(128)),
        )
        self.rotki.setup_exchange(
            name='binance',
            api_key=str(make_random_b64bytes(128)),
            api_secret=str(make_random_b64bytes(128)),
        )

        self.writer = ActionWriter(
            trades_number=args.trades_number,
            rotkehlchen=self.rotki,
            fake_kraken=self.fake_kraken,
            fake_binance=self.fake_binance,
        )

        self.writer.generate_history()
        # stop the fake exchange API. Will be started again once we are finished,
        # ready to serve the Rotkehlchen client
        self.mock_server.stop()

    def create_new_user(self, user_name: Optional[str], given_password: str):
        if not user_name:
            user_name = self.faker.user_name()

        logger.info(f'Creating fake user {user_name} with password {given_password}')

        self.rotki.unlock_user(
            user=user_name,
            password=given_password,
            create_new=True,
            sync_approval=False,
            api_key='',
            api_secret='',
        )
