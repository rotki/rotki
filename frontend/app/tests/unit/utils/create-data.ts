import type { AssetPrice } from '@/modules/assets/prices/price-types';
import type { Exchange } from '@/modules/balances/types/exchanges';
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

/**
 * A connection that synced cleanly and was never synced, unless `syncStatus` says otherwise. Its
 * identifier is its connector and name joined, so two connections share one only when both match.
 */
export function createTestBankConnection(
  connector: string,
  name: string,
  syncStatus: Partial<BankConnection['syncStatus']> = {},
): BankConnection {
  return {
    bankCode: null,
    connector,
    displayName: connector,
    identifier: `${connector}-${name}`,
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

/**
 * A connected exchange as the backend lists it. The identifier is derived from the location and
 * name, so a spec can predict it without holding the object.
 */
export function createTestExchange(location: string, name: string, extras: Partial<Exchange> = {}): Exchange {
  return { connector: location, identifier: `${location}-${name}`, location, name, ...extras };
}
