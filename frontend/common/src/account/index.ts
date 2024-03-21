export interface AccountData {
  readonly address: string;
  readonly label: string;
  readonly tags: string[];
}

export interface Account {
  readonly chain: string;
  readonly address: string;
}

export interface GeneralAccount extends AccountData, Account {}
