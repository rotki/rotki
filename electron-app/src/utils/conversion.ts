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
