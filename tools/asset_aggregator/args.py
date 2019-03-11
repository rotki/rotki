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
    return p
