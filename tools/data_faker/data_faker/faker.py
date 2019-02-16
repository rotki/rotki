import datetime
import logging
import random
from typing import Optional

from data_faker.actions import ActionWriter
from data_faker.fake_kraken import FakeKraken
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
        # register the exchanges with the rotkehlchen DB of the new user
        self.rotki.data.db.add_exchange(
            name='kraken',
            api_key=make_random_b64bytes(128),
            api_secret=make_random_b64bytes(128),
        )

        self.fake_kraken = FakeKraken()
        self.writer = ActionWriter(
            trades_number=args.trades_number,
            rotkehlchen=self.rotki,
            fake_kraken=self.fake_kraken,
        )

        self.writer.generate_history()

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
