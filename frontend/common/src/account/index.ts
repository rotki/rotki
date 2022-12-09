import { type Blockchain, type DefiProtocol } from '../blockchain';

export interface AccountData {
  readonly address: string;
  readonly label: string;
  readonly tags: string[];
}

export interface Account {
  readonly chain: Blockchain;
  readonly address: string;
}

export interface DefiAccount extends Account {
  readonly protocols: DefiProtocol[];
}

export interface GeneralAccount extends AccountData, Account {}
