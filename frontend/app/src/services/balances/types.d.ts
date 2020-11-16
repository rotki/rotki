import { default as BigNumber } from 'bignumber.js';
import { exchanges } from '@/data/defaults';
import { Balance } from '@/services/types-api';
import { Location } from '@/services/types-common';

export type SupportedExchange = typeof exchanges[number];

export interface ManualBalance {
  readonly asset: string;
  readonly label: string;
  readonly amount: BigNumber;
  readonly location: Location;
  readonly tags: string[];
}

export interface ManualBalanceWithValue extends ManualBalance {
  readonly usdValue: BigNumber;
}

export interface ManualBalances {
  readonly balances: ManualBalanceWithValue[];
}

interface BlockchainTotals {
  readonly assets: Balances;
  readonly liabilities: Balances;
}

export interface BlockchainBalances {
  readonly perAccount: {
    ETH: EthBalances;
    BTC: BtcBalances;
  };
  readonly totals: BlockchainTotals;
}

interface XpubBalance {
  readonly xpub: string;
  readonly derivationPath: string;
  readonly addresses: Balances;
}

interface BtcBalances {
  readonly standalone: Balances;
  readonly xpubs: XpubBalance[];
}

export interface EthBalance {
  readonly assets: Balances;
  readonly liabilities: Balances;
}

export interface EthBalances {
  [account: string]: EthBalance;
}

export interface Balances {
  [account: string]: Balance;
}
