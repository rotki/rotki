/**
 * Digit prefix typed into the DateTimePicker (DD/MM/YYYY HH:mm).
 * The seconds and milliseconds are appended dynamically by fillDatetime()
 * so each event gets a unique, incrementing timestamp for predictable ordering.
 */
export const TEST_EVENT_DATE_DIGITS = '150120241200';

/** Unix timestamp in seconds matching the test date (for price seeding). */
export const TEST_EVENT_TIMESTAMP = 1705320000;

/** All asset identifiers used in tests, with approximate USD prices for the test date. */
export const TEST_PRICE_ENTRIES: { fromAsset: string; price: string }[] = [
  { fromAsset: 'ETH', price: '2500' },
  { fromAsset: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', price: '1' },
  { fromAsset: 'SOL', price: '100' },
  { fromAsset: 'solana/token:4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R', price: '0.5' },
  { fromAsset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', price: '1' },
  { fromAsset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', price: '2500' },
];

export interface OnlineEventFixture {
  location: string;
  eventType: string;
  eventSubtype: string;
  asset: string;
  assetId?: string;
  amount: string;
  notes: string;
}

export interface SwapSubEventFixture {
  asset: string;
  assetId?: string;
  amount: string;
}

export type SwapFeeFixture = SwapSubEventFixture;

export interface SwapEventFixture {
  location: string;
  spendAsset: string;
  spendAssetId?: string;
  spendAmount: string;
  receiveAsset: string;
  receiveAssetId?: string;
  receiveAmount: string;
  fee?: SwapFeeFixture;
}

export interface AssetMovementEventFixture {
  location: string;
  eventSubtype: string;
  asset: string;
  assetId?: string;
  amount: string;
  notes: string;
}

export const onlineEventFixture: OnlineEventFixture = {
  amount: '1.5',
  asset: 'ETH',
  eventSubtype: 'airdrop',
  eventType: 'receive',
  location: 'kraken',
  notes: 'E2E test online event',
};

export const swapEventFixture: SwapEventFixture = {
  fee: {
    amount: '0.005',
    asset: 'ETH',
  },
  location: 'kraken',
  receiveAmount: '3000',
  receiveAsset: 'DAI',
  receiveAssetId: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
  spendAmount: '1',
  spendAsset: 'ETH',
};

export const assetMovementEventFixture: AssetMovementEventFixture = {
  amount: '0.5',
  asset: 'ETH',
  eventSubtype: 'receive',
  location: 'kraken',
  notes: 'E2E test deposit event',
};

export interface SolanaEventFixture {
  txRef: string;
  eventType: string;
  eventSubtype: string;
  asset: string;
  assetId?: string;
  amount: string;
  notes: string;
}

export interface SolanaSwapEventFixture {
  txRef: string;
  spendAsset: string;
  spendAssetId?: string;
  spendAmount: string;
  receiveAsset: string;
  receiveAssetId?: string;
  receiveAmount: string;
}

export interface EthBlockEventFixture {
  blockNumber: string;
  validatorIndex: string;
  amount: string;
  feeRecipient: string;
  isMevReward: boolean;
}

export interface EthWithdrawalEventFixture {
  validatorIndex: string;
  amount: string;
  withdrawalAddress: string;
  isExit: boolean;
}

export const solanaEventFixture: SolanaEventFixture = {
  amount: '2.5',
  asset: 'SOL',
  eventSubtype: 'airdrop',
  eventType: 'receive',
  notes: 'E2E test solana event',
  txRef: '5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW',
};

export const solanaSwapEventFixture: SolanaSwapEventFixture = {
  receiveAmount: '1.5',
  receiveAsset: 'SOL',
  spendAmount: '50',
  spendAsset: 'RAY',
  spendAssetId: 'solana/token:4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R',
  txRef: '3nGJm9dqGhfyJzkLhL7KMQqGGQqyL5aLqWJNF8JvqSDqWqCRAkVVdDhTZmTHJHVQtDk3LLwYvBSVCH9Tg4CKnWqA',
};

export const ethBlockEventFixture: EthBlockEventFixture = {
  amount: '0.05',
  blockNumber: '19000000',
  feeRecipient: '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045',
  isMevReward: false,
  validatorIndex: '100000',
};

export const ethWithdrawalEventFixture: EthWithdrawalEventFixture = {
  amount: '32',
  isExit: false,
  validatorIndex: '100001',
  withdrawalAddress: '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045',
};

export interface EthDepositEventFixture {
  validatorIndex: string;
  txHash: string;
  amount: string;
  depositor: string;
}

export const ethDepositEventFixture: EthDepositEventFixture = {
  amount: '32',
  depositor: '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045',
  txHash: '0xaa1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b',
  validatorIndex: '100002',
};

export interface EvmEventFixture {
  txRef: string;
  eventType: string;
  eventSubtype: string;
  asset: string;
  assetId?: string;
  amount: string;
  notes: string;
}

export interface EvmSwapEventFixture {
  txRef: string;
  spendAsset: string;
  spendAssetId?: string;
  spendAmount: string;
  receiveAsset: string;
  receiveAssetId?: string;
  receiveAmount: string;
}

export interface EvmMultiSwapEventFixture {
  txRef: string;
  spend: SwapSubEventFixture[];
  receive: SwapSubEventFixture[];
  fees: SwapSubEventFixture[];
}

export const evmEventFixture: EvmEventFixture = {
  amount: '1.5',
  asset: 'ETH',
  eventSubtype: 'airdrop',
  eventType: 'receive',
  notes: 'E2E test evm event',
  txRef: '0x523b7df8e168315e97a836a3d516d639908814785d7df1ef1745de3e55501982',
};

export const evmSwapEventFixture: EvmSwapEventFixture = {
  receiveAmount: '3000',
  receiveAsset: 'DAI',
  receiveAssetId: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
  spendAmount: '1',
  spendAsset: 'ETH',
  txRef: '0x6f1e170e02000545cafe5d10a4277e9c0c009c1085c3fd06a5c75443cadf2a75',
};

export const evmMultiSwapEventFixture: EvmMultiSwapEventFixture = {
  fees: [
    { amount: '0.005', asset: 'ETH' },
    {
      amount: '2',
      asset: 'DAI',
      assetId: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
    },
  ],
  receive: [
    {
      amount: '3000',
      asset: 'DAI',
      assetId: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
    },
    {
      amount: '500',
      asset: 'USDC',
      assetId: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    },
  ],
  spend: [
    { amount: '1', asset: 'ETH' },
    {
      amount: '0.5',
      asset: 'WETH',
      assetId: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    },
  ],
  txRef: '0xa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
};
