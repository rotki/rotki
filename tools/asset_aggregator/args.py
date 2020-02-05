import argparse


def aggregator_args() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='Asset aggregator',
        description=(
            'A tool to help cross-check, maintain and populate the '
            'Rotkehlchen assets list',
        ),
    )
    p.add_argument(
        '--cmc-api-key',
        help='If given we are trying to use coinmarketcap in the aggregator',
    )
    p.add_argument(
        '--always-keep-our-time',
        action='store_true',
        help=(
            'If given then we always keep our started times if they exist  '
            'and we do not compare to other APIs',
        ),
    )
    p.add_argument(
        '--input-file',
        help=(
            'A path to a secondary file for new assets to be added. If given, then '
            'only the assets of that file are checked. Used for faster addition '
            'of new assets to the assets list. Can not be combined with --process-eth-tokens',
        ),
    )
    p.add_argument(
        '--db-user',
        help='The DB username to connect to'
    )
    p.add_argument(
        '--db-password',
        help='The password to use to connect to the DB'
    )
    return p
