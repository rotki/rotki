import { YEARN_EVENTS, YEARN_VAULTS } from '@/services/defi/types/consts';
import { Balance } from '@/services/types-api';

export type SupportedYearnVault = typeof YEARN_VAULTS[number];

type YearnEventType = typeof YEARN_EVENTS[number];

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
  readonly [vault in SupportedYearnVault]?: YearnVault;
};

export interface YearnVaultsHistory {
  readonly [address: string]: AccountYearnVault;
}

export interface YearnVaultProfitLoss {
  readonly value: Balance;
  readonly asset: string;
  readonly vault: SupportedYearnVault;
}

interface YearnVaultBalance {
  readonly underlyingToken: string;
  readonly vaultToken: string;
  readonly underlyingValue: Balance;
  readonly vaultValue: Balance;
  readonly roi: string;
}

export interface YearnVaultAsset extends YearnVaultBalance {
  readonly vault: SupportedYearnVault;
}

type AccountYearnVaultEntry = {
  readonly [vault in SupportedYearnVault]?: YearnVaultBalance;
};

export interface YearnVaultsBalances {
  readonly [address: string]: AccountYearnVaultEntry;
}
