import type { AssetBreakdown } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { createTestBalance, createTestManualBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { createAccount, createValidatorAccount } from '@/modules/accounts/create-account';
import { BalanceType } from '@/modules/balances/types/balances';
import { assetBreakdown, assetsAtLocation, type BreakdownInputs, type BreakdownPorts, mergedBreakdown } from './asset-breakdown';

const ports: BreakdownPorts = {
  chainLabel: chain => (chain === 'eth' ? 'ethereum' : chain),
  resolveIdentifier: identifier => (identifier === 'ETH2' ? 'ETH' : identifier),
};

const inputs: BreakdownInputs = {
  accounts: {
    eth: [
      createAccount({ address: '0x1', label: null, tags: ['hot'] }, { chain: 'eth', nativeAsset: 'ETH' }),
      createAccount({ address: '0x2', label: null, tags: null }, { chain: 'eth', nativeAsset: 'ETH' }),
    ],
    optimism: [createAccount({ address: '0x1', label: null, tags: ['l2'] }, { chain: 'optimism', nativeAsset: 'ETH' })],
  },
  balances: {
    eth: {
      '0x1': {
        assets: { ETH: { 'address': createTestBalance(1, 10), 'uniswap-v3': createTestBalance(2, 20) } },
        liabilities: { ETH: { aave: createTestBalance(1, 10) } },
      },
      '0x2': { assets: { ETH: { address: createTestBalance(0, 0) } }, liabilities: {} },
    },
    optimism: { '0x1': { assets: { ETH: { address: createTestBalance(5, 50) } }, liabilities: {} } },
  },
  exchanges: { kraken: { ETH: createTestBalance(4, 40), ETH2: createTestBalance(1, 10) } },
  manual: [
    { ...createTestManualBalance('ETH2', 7, 70, 'external', BalanceType.ASSET, 1), tags: ['cold'] },
    createTestManualBalance('BTC', 1, 1, 'external', BalanceType.ASSET, 2),
  ],
};

function plain(rows: AssetBreakdown[]): unknown {
  return JSON.parse(JSON.stringify(rows));
}

describe('assetBreakdown', () => {
  it('should list every account, exchange and manual location holding the asset, highest value first', () => {
    expect(plain(assetBreakdown('ETH', inputs, false, {}, ports))).toEqual([
      { address: '', amount: '7', location: 'external', tags: ['cold'], value: '70' },
      { address: '0x1', amount: '5', location: 'optimism', tags: ['l2'], value: '50' },
      { address: '', amount: '5', location: 'kraken', value: '50' },
      { address: '0x1', amount: '3', location: 'ethereum', tags: ['hot'], value: '30' },
    ]);
  });

  it('should narrow to on-chain accounts when a chain, an account or blockchainOnly is given', () => {
    const locations = (filters: object): string[] =>
      assetBreakdown('ETH', inputs, false, filters, ports).map(row => `${row.location}:${row.address}`);

    expect(locations({ chains: ['eth'] })).toEqual(['ethereum:0x1']);
    expect(locations({ groupId: '0x1' })).toEqual(['optimism:0x1', 'ethereum:0x1']);
    expect(locations({ blockchainOnly: true })).toEqual(['optimism:0x1', 'ethereum:0x1']);
  });

  it('should read liabilities from accounts and manual liabilities, never from exchanges', () => {
    const liabilities = { ...inputs, manual: [createTestManualBalance('ETH', 2, 20, 'bank', BalanceType.LIABILITY, 3)] };
    expect(plain(assetBreakdown('ETH', liabilities, true, {}, ports))).toEqual([
      { address: '', amount: '2', location: 'bank', value: '20' },
      { address: '0x1', amount: '1', location: 'ethereum', tags: ['hot'], value: '10' },
    ]);
  });

  it('should leave out rows holding nothing', () => {
    const addresses = assetBreakdown('ETH', inputs, false, { chains: ['eth'] }, ports).map(row => row.address);
    expect(addresses).not.toContain('0x2');
  });
});

describe('assetBreakdown with an asset treated as another', () => {
  const staking: BreakdownInputs = {
    accounts: {
      eth: [createAccount({ address: '0x1', label: null, tags: null }, { chain: 'eth', nativeAsset: 'ETH' })],
      eth2: [createValidatorAccount({ index: 1, publicKey: '0xvalidator', status: 'active' }, { chain: 'eth2', nativeAsset: 'ETH' })],
    },
    balances: {
      eth: { '0x1': { assets: { ETH: { address: createTestBalance(1, 10) } }, liabilities: {} } },
      eth2: { '0xvalidator': { assets: { ETH2: { address: createTestBalance(32, 320) } }, liabilities: {} } },
    },
    exchanges: { kraken: { ETH2: createTestBalance(2, 20) } },
    manual: [],
  };

  function locations(asset: string): string[] {
    return assetBreakdown(asset, staking, false, {}, ports).map(row => `${row.location}:${row.amount.toFixed()}`);
  }

  it('should list the validator rows of the merged asset alongside its other holdings', () => {
    expect(locations('ETH')).toEqual(['eth2:32', 'kraken:2', 'ethereum:1']);
  });

  it('should list only the asset itself when asked for the identifier that is merged away', () => {
    expect(locations('ETH2')).toEqual(['eth2:32', 'kraken:2']);
  });
});

describe('mergedBreakdown', () => {
  it('should merge the rows of several assets that share a location', () => {
    const merged = mergedBreakdown({
      ETH: [{ address: '0x1', amount: bigNumberify(1), location: 'ethereum', value: bigNumberify(10) }],
      WETH: [{ address: '0x1', amount: bigNumberify(2), location: 'ethereum', value: bigNumberify(20) }],
    }, row => row.location);
    expect(plain(merged)).toEqual([{ address: '0x1', amount: '3', location: 'ethereum', value: '30' }]);
  });
});

describe('assetsAtLocation', () => {
  it('should list what each asset holds at the location, skipping assets absent from it', () => {
    const held = assetsAtLocation({
      ETH: [{ address: '', amount: bigNumberify(1), location: 'kraken', value: bigNumberify(10) }],
      WETH: [{ address: '', amount: bigNumberify(2), location: 'binance', value: bigNumberify(20) }],
    }, 'kraken');
    expect(held.map(({ asset, amount }) => `${asset}:${amount.toFixed()}`)).toEqual(['ETH:1']);
  });
});
