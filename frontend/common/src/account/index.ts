export interface Account {
  readonly chain: string;
  readonly address: string;
}

export interface GeneralAccount {
  readonly data: { address: string };
  readonly tags?: string[];
  readonly label?: string;
  readonly chain: string;
  readonly nativeAsset: string;
  readonly groupId?: string;
  readonly groupHeader?: boolean;
}
