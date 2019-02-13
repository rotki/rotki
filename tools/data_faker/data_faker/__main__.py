from gevent import monkey  # isort:skip # noqa
monkey.patch_all()  # isort:skip # noqa
import logging

from data_faker.args import data_faker_args
from data_faker.faker import DataFaker

logger = logging.getLogger(__name__)


def main():
    arg_parser = data_faker_args()
    args = arg_parser.parse_args()
    DataFaker(args)


if __name__ == '__main__':
    main()
