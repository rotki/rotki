import argparse
import datetime
import logging
import random
from string import ascii_uppercase, digits
from typing import Optional

from data_faker.actions import ActionWriter
from data_faker.fake_binance import FakeBinance
from data_faker.fake_kraken import FakeKraken
from data_faker.mock_apis.api import APIServer, RestAPI

from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.factories import make_random_b64bytes
from rotkehlchen.typing import ApiKey, ApiSecret

logger = logging.getLogger(__name__)


class DataFaker():

    def __init__(self, args: argparse.Namespace) -> None:
        args.logfile = 'data_faker.log'
        self.rotki = Rotkehlchen(args)

        random_seed = datetime.datetime.now()
        logger.info(f'Random seed used: {random_seed}')
        random.seed(random_seed)

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
            api_key=ApiKey(str(make_random_b64bytes(128))),
            api_secret=ApiSecret(make_random_b64bytes(128)),
        )
        self.rotki.setup_exchange(
            name='binance',
            api_key=ApiKey(str(make_random_b64bytes(128))),
            api_secret=ApiSecret(make_random_b64bytes(128)),
        )

        self.writer = ActionWriter(
            trades_number=args.trades_number,
            seconds_between_trades=args.seconds_between_trades,
            seconds_between_balance_save=args.seconds_between_balance_save,
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
            user_name = ''.join(random.choices(ascii_uppercase + digits, k=10))

        logger.info(f'Creating fake user {user_name} with password {given_password}')

        self.rotki.unlock_user(
            user=user_name,
            password=given_password,
            create_new=True,
            sync_approval='no',
            premium_credentials=None,
        )
