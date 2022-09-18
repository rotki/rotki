import { Balance } from '@rotki/common';
import { ProtocolVersion } from '@/services/defi/consts';

export const WITHDRAW = 'withdraw';
export const DEPOSIT = 'deposit';
export const YEARN_EVENTS = [WITHDRAW, DEPOSIT] as const;

export type YearnEventType = typeof YEARN_EVENTS[number];

interface YearnVaultEvent {
  readonly eventType: YearnEventType;
  readonly blockNumber: number;
  readonly timestamp: number;
  readonly fromAsset: string;
  readonly fromValue: Balance;
  readonly toAsset: string;
  readonly toValue: Balance;
  readonly realizedPnl: Balance | null;
  readonly txHash: string;
  readonly logIndex: number;
}

interface YearnVault {
  readonly events: YearnVaultEvent[];
  readonly profitLoss: Balance;
}

type AccountYearnVault = {
  readonly [vault: string]: YearnVault;
};

export interface YearnVaultsHistory {
  readonly [address: string]: AccountYearnVault;
}

export interface YearnVaultProfitLoss {
  readonly value: Balance;
  readonly asset: string;
  readonly vault: string;
}

export interface YearnVaultBalance {
  readonly underlyingToken: string;
  readonly vaultToken: string;
  readonly underlyingValue: Balance;
  readonly vaultValue: Balance;
  readonly roi: string;
}

export interface YearnVaultAsset extends YearnVaultBalance {
  readonly vault: string;
  readonly version: ProtocolVersion;
}

type AccountYearnVaultEntry = {
  readonly [vault: string]: YearnVaultBalance;
};

export interface YearnVaultsBalances {
  readonly [address: string]: AccountYearnVaultEntry;
}
