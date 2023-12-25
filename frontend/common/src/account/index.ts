import { type Blockchain } from '../blockchain';

export interface AccountData {
  readonly address: string;
  readonly label: string;
  readonly tags: string[];
}

export interface Account<T = Blockchain> {
  readonly chain: T;
  readonly address: string;
}

export interface GeneralAccount<T = Blockchain>
  extends AccountData,
    Account<T> {}
