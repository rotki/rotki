import type { Blockchain } from '@rotki/common';

export interface FixtureBlockchainAccount {
  readonly blockchain: Blockchain;
  readonly inputMode: string;
  readonly chainName: string;
  readonly address: string;
  readonly label: string;
  readonly tags: string[];
}

export interface FixtureManualBalance {
  readonly asset: string;
  readonly keyword: string;
  readonly label: string;
  readonly amount: string;
  readonly location: string;
  readonly tags: string[];
}
