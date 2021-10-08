import { Balance } from "../../index";

export interface Eth2Deposit {
  readonly fromAddress: string;
  readonly pubkey: string;
  readonly withdrawalCredentials: string;
  readonly value: Balance;
  readonly depositIndex: number;
  readonly txHash: string;
  readonly logIndex: number;
}

export interface Eth2DailyStat {
  readonly timestamp: number;
  readonly pnl: Balance;
  readonly startBalance: Balance;
  readonly endBalance: Balance;
  readonly missedAttestations: number;
  readonly orphanedAttestations: number;
  readonly proposedBlocks: number;
  readonly missedBlocks: number;
  readonly orphanedBlocks: number;
  readonly includedAttesterSlashings: number;
  readonly proposerAttesterSlashings: number;
  readonly depositsNumber: number;
  readonly depositedBalance: Balance;
}

export interface Eth2Detail {
  readonly eth1Depositor: string;
  readonly publicKey: string;
  readonly index: number;
  readonly balance: Balance;
  readonly performance1d: Balance;
  readonly performance1w: Balance;
  readonly performance1m: Balance;
  readonly performance1y: Balance;
  readonly dailyStats: Eth2DailyStat[];
}


export interface Eth2DailyStatWithIndex extends Eth2DailyStat {
  readonly index: number;
}