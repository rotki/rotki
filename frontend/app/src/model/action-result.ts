interface ApiKey {
  api_key: string;
}

export interface ExternalServiceKeys {
  etherscan?: ApiKey;
  cryptocompare?: ApiKey;
  covalent?: ApiKey;
  beaconchain?: ApiKey;
  loopring?: ApiKey;
}
