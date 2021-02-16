import argparse
import operator
import random
import sys
from typing import Tuple

from rotkehlchen.accounting.structures import BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.config import default_data_directory
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_location
from rotkehlchen.typing import Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now


def divide_number_in_parts(number: int, parts_number: int):
    if parts_number > number:
        raise ValueError('Number of parts cant be higher than the number')
    number_rest = number

    for i in range(1, parts_number + 1):
        if i == parts_number:
            yield number_rest
            break

        new_number = random.randint(1, (number_rest - (parts_number - i)) // 2)
        number_rest -= new_number
        yield new_number


class StatisticsFaker():

    def __init__(self, args: argparse.Namespace) -> None:
        self.db = DBHandler(
            user_data_dir=default_data_directory() / args.user_name,
            password=args.user_password,
            msg_aggregator=MessagesAggregator(),
            initial_settings=None,
        )

    def _clean_tables(self) -> None:
        cursor = self.db.conn.cursor()
        cursor.execute('DELETE from timed_location_data;')
        cursor.execute('DELETE from timed_balances;')
        self.db.conn.commit()

    @staticmethod
    def _get_amounts(args: argparse.Namespace) -> Tuple[int, int, int]:
        if not isinstance(args.min_amount, int) and args.min_amount < 0:
            print('Invalid minimum amount given')
            sys.exit(1)
        min_amount = args.min_amount

        if not isinstance(args.max_amount, int) or args.max_amount < min_amount:
            print('Invalid max amount given')
            sys.exit(1)
        max_amount = args.max_amount

        invalid_starting_amount = (
            not isinstance(args.starting_amount, int) or
            args.starting_amount < min_amount or
            args.starting_amount > max_amount
        )
        if invalid_starting_amount:
            print('Invalid starting amount given')
            sys.exit(1)
        starting_amount = args.starting_amount

        return starting_amount, min_amount, max_amount

    @staticmethod
    def _get_timestamps(args: argparse.Namespace) -> Tuple[Timestamp, Timestamp]:
        if not isinstance(args.from_timestamp, int) or args.from_timestamp < 0:
            print('Invalid from timestamp given')
            sys.exit(1)
        from_ts = Timestamp(args.from_timestamp)

        if args.to_timestamp is None:
            to_ts = ts_now()
        else:
            if not isinstance(args.to_timestamp, int) or args.to_timestamp < from_ts:
                print('Invalid to timestamp given')
                sys.exit(1)

            to_ts = Timestamp(args.to_timestamp)

        return from_ts, to_ts

    def create_fake_data(self, args: argparse.Namespace) -> None:
        self._clean_tables()
        from_ts, to_ts = StatisticsFaker._get_timestamps(args)
        starting_amount, min_amount, max_amount = StatisticsFaker._get_amounts(args)
        total_amount = starting_amount
        locations = [deserialize_location(location) for location in args.locations.split(',')]
        assets = [Asset(symbol) for symbol in args.assets.split(',')]
        go_up_probability = FVal(args.go_up_probability)

        # Add the first distribution of location data
        location_data = []
        for idx, value in enumerate(divide_number_in_parts(starting_amount, len(locations))):
            location_data.append(LocationData(
                time=from_ts,
                location=locations[idx].serialize_for_db(),
                usd_value=str(value),
            ))
        # add the location data + total to the DB
        self.db.add_multiple_location_data(location_data + [LocationData(
            time=from_ts,
            location=Location.TOTAL.serialize_for_db(),
            usd_value=str(total_amount),
        )])

        # Add the first distribution of assets
        assets_data = []
        for idx, value in enumerate(divide_number_in_parts(starting_amount, len(assets))):
            assets_data.append(DBAssetBalance(
                category=BalanceType.ASSET,
                time=from_ts,
                asset=assets[idx],
                amount=str(random.randint(1, 20)),
                usd_value=str(value),
            ))
        self.db.add_multiple_balances(assets_data)

        while from_ts < to_ts:
            print(f'At timestamp: {from_ts}/{to_ts} wih total net worth: ${total_amount}')
            new_location_data = []
            new_assets_data = []
            from_ts += args.seconds_between_balance_save
            # remaining_loops = to_ts - from_ts / args.seconds_between_balance_save
            add_usd_value = random.choice([100, 350, 500, 625, 725, 915, 1000])
            add_amount = random.choice([
                FVal('0.1'), FVal('0.23'), FVal('0.34'), FVal('0.69'), FVal('1.85'), FVal('2.54'),
            ])

            go_up = (
                # If any asset's usd value is close to to go below zero, go up
                any(FVal(a.usd_value) - FVal(add_usd_value) < 0 for a in assets_data) or
                # If total is going under the min amount go up
                total_amount - add_usd_value < min_amount or
                # If "dice roll" matched and we won't go over the max amount go up
                (
                    add_usd_value + total_amount < max_amount and
                    FVal(random.random()) <= go_up_probability
                )
            )
            if go_up:
                total_amount += add_usd_value
                action = operator.add
            else:
                total_amount -= add_usd_value
                action = operator.sub

            for idx, value in enumerate(divide_number_in_parts(add_usd_value, len(locations))):
                new_location_data.append(LocationData(
                    time=from_ts,
                    location=location_data[idx].location,
                    usd_value=str(action(FVal(location_data[idx].usd_value), value)),
                ))
            # add the location data + total to the DB
            self.db.add_multiple_location_data(new_location_data + [LocationData(
                time=from_ts,
                location=Location.TOTAL.serialize_for_db(),
                usd_value=str(total_amount),
            )])

            for idx, value in enumerate(divide_number_in_parts(add_usd_value, len(assets))):
                old_amount = FVal(assets_data[idx].amount)
                new_amount = action(old_amount, add_amount)
                if new_amount < FVal('0'):
                    new_amount = old_amount + FVal('0.01')
                new_assets_data.append(DBAssetBalance(
                    category=BalanceType.ASSET,
                    time=from_ts,
                    asset=assets[idx],
                    amount=str(new_amount),
                    usd_value=str(action(FVal(assets_data[idx].usd_value), value)),
                ))
            self.db.add_multiple_balances(new_assets_data)

            location_data = new_location_data
            assets_data = new_assets_data
