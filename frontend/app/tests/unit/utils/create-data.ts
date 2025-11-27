import type { ManualBalanceWithPrice } from '@/types/manual-balances';
import type { AssetPrice } from '@/types/prices';
import { type Balance, bigNumberify, type ProtocolBalance } from '@rotki/common';
import { BalanceType } from '@/types/balances';

export function createTestBalanceResponse(amount: number, usdValue: number, value?: number): {
  amount: string;
  usdValue: string;
  value: string;
} {
  return {
    amount: amount.toString(),
    usdValue: usdValue.toString(),
    value: (value ?? usdValue).toString(),
  };
}

export function createTestBalance(amount: number, usdValue: number, value?: number): Balance {
  return {
    amount: bigNumberify(amount),
    usdValue: bigNumberify(usdValue),
    value: bigNumberify(value ?? usdValue),
  };
}

export function createProtocolTestBalance(protocol: string, amount: number, usdValue: number, containsManual?: boolean): ProtocolBalance {
  return {
    protocol,
    ...createTestBalance(amount, usdValue),
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
  usdValue: number,
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
    usdValue: bigNumberify(usdValue),
    value: bigNumberify(usdValue),
  };
}
