import type { ManualBalanceWithPrice } from '@/types/manual-balances';
import type { AssetPrice } from '@/types/prices';
import { type Balance, bigNumberify, type ProtocolBalance } from '@rotki/common';
import { BalanceType } from '@/types/balances';

export function createTestBalanceResponse(amount: number, value: number): {
  amount: string;
  value: string;
} {
  return {
    amount: amount.toString(),
    value: value.toString(),
  };
}

export function createTestBalance(amount: number, value: number): Balance {
  return {
    amount: bigNumberify(amount),
    value: bigNumberify(value),
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
