import {
  AccountTokens,
  ApiBalances,
  ApiEthBalances,
  Balances,
  EthBalances
} from '@/model/blockchain-balances';

import { bigNumberify } from '@/utils/bignumbers';
import omit from 'lodash/omit';
import transform from 'lodash/transform';

export function convertEthBalances(apiBalances: ApiEthBalances): EthBalances {
  const balances: EthBalances = {};
  for (const account in apiBalances) {
    if (!apiBalances.hasOwnProperty(account)) {
      continue;
    }

    const balance = apiBalances[account];
    const tokens = omit(balance, ['ETH', 'usd_value']);
    const accountTokens = transform(
      tokens,
      (result: AccountTokens, value: string, key: string) => {
        result[key] = bigNumberify(value);
      },
      {}
    );

    balances[account] = {
      eth: bigNumberify(balance.ETH as string),
      usdValue: bigNumberify(balance.usd_value as string),
      tokens: accountTokens
    };
  }
  return balances;
}

export function convertBalances(apiBalances: ApiBalances): Balances {
  const balances: Balances = {};
  for (const account in apiBalances) {
    if (!apiBalances.hasOwnProperty(account)) {
      continue;
    }
    balances[account] = {
      amount: bigNumberify(apiBalances[account].amount as string),
      usdValue: bigNumberify(apiBalances[account].usd_value as string)
    };
  }
  return balances;
}

export function convertToTimestamp(date: string): number {
  const fields = date.match(/\d+/g);
  if (!fields) {
    return -1;
  }

  const day = parseInt(fields[0], 10);
  const month = parseInt(fields[1], 10) - 1;
  const year = parseInt(fields[2], 10);
  const hours = parseInt(fields[3], 10);
  const seconds = parseInt(fields[4], 10);
  return new Date(Date.UTC(year, month, day, hours, seconds)).getTime() / 1000;
}
