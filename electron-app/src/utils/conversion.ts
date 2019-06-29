import { EthBalances } from '@/model/blockchain-balances';
import { Balances } from '@/typing/types';

export function convertEthBalances(apiBalances: Balances): EthBalances {
  const balances: EthBalances = {};
  for (const account in apiBalances) {
    balances[account] = {
      eth: parseFloat(apiBalances[account]['ETH'] as string),
      usdValue: parseFloat(apiBalances[account].usd_value as string)
    };
  }
  return balances;
}
