from gevent import monkey  # isort:skip # noqa
monkey.patch_all()  # isort:skip # noqa
import logging

from data_faker.args import data_faker_args
from data_faker.faker import DataFaker
from data_faker.mock_apis.api import APIServer, RestAPI
from data_faker.statistics import StatisticsFaker

logger = logging.getLogger(__name__)


def main() -> None:
    arg_parser = data_faker_args()
    args = arg_parser.parse_args()
    if args.command == 'mockall':
        faker = DataFaker(args)

        rest_api = RestAPI(
            fake_kraken=faker.fake_kraken,
            fake_binance=faker.fake_binance,
        )
        server = APIServer(rest_api)
        print('SERVER IS NOW RUNNING')
        # For some reason debug=True throws an exception:
        # ModuleNotFoundError: No module named 'data_faker
        # server.run(debug=True)
        server.run()
        print('SERVER IS NOW SHUTTING DOWN')
    elif args.command == 'statistics':
        stats_faker = StatisticsFaker(args)
        stats_faker.create_fake_data(args)
    else:
        raise AssertionError(f'Should not happen. Unexpected command {args.command} given')


if __name__ == '__main__':
    main()
