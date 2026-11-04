import type { AssetPrice } from '@/modules/assets/prices/price-types';
import type { ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import type { BankConnection } from '@/modules/banks/types';
import { type Balance, bigNumberify, type ProtocolBalance } from '@rotki/common';
import { BalanceType } from '@/modules/balances/types/balances';

export function createTestBalance(amount: number, value: number): Balance {
  return {
    amount: bigNumberify(amount),
    value: bigNumberify(value),
  };
}

/** A connection that synced cleanly and was never synced, unless `syncStatus` says otherwise. */
export function createTestBankConnection(
  connector: string,
  name: string,
  syncStatus: Partial<BankConnection['syncStatus']> = {},
): BankConnection {
  return {
    bankCode: null,
    connector,
    displayName: connector,
    name,
    syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false, ...syncStatus },
  };
}

export function createProtocolTestBalance(protocol: string, amount: number, value: number, containsManual?: boolean): ProtocolBalance {
  return {
    protocol,
    ...createTestBalance(amount, value),
    ...(containsManual ? { containsManual } : {}),
  };
}

export function createTestPriceInfo(value: number, oracle = 'coingecko', isManual = false, usdPrice?: number): AssetPrice {
  return {
    isManualPrice: isManual,
    oracle,
    value: bigNumberify(value),
    ...(usdPrice !== undefined ? { usdPrice: bigNumberify(usdPrice) } : {}),
  };
}

export function createTestManualBalance(
  asset: string,
  amount: number,
  value: number,
  location: string,
  balanceType = BalanceType.ASSET,
  id = 1,
): ManualBalanceWithPrice {
  return {
    amount: bigNumberify(amount),
    asset,
    balanceType,
    identifier: id,
    label: `Test ${asset}`,
    location,
    tags: [],
    value: bigNumberify(value),
  };
}
