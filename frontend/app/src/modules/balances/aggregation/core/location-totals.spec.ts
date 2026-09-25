import type { Balances } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { blockchainValue, totalsByChainLocation, totalsByLocation } from './location-totals';

const balances: Balances = {
  eth: {
    '0x1': {
      assets: {
        ETH: { 'address': createTestBalance(1, 100), 'uniswap-v3': createTestBalance(1, 50) },
        SPAM: { address: createTestBalance(1000, 1) },
      },
      liabilities: { DAI: { makerdao: createTestBalance(10, 10) } },
    },
    '0x2': { assets: { ETH: { address: createTestBalance(1, 100) } }, liabilities: {} },
  },
  optimism: { '0x1': { assets: { ETH: { address: createTestBalance(1, 7) } }, liabilities: {} } },
  polygon: { '0x1': { assets: { SPAM: { address: createTestBalance(1, 3) } }, liabilities: {} } },
};

const isAssetIgnored = (identifier: string): boolean => identifier === 'SPAM';

function plain(totals: Record<string, { toFixed: () => string }>): Record<string, string> {
  return Object.fromEntries(Object.entries(totals).map(([key, value]) => [key, value.toFixed()]));
}

describe('blockchainValue', () => {
  it('should sum every protocol of every account on every chain, leaving ignored assets and liabilities out', () => {
    expect(blockchainValue(balances, isAssetIgnored).toFixed()).toBe('257');
  });

  it('should count an account that arrived without assets as nothing', () => {
    const partial: Balances = { eth: { '0x1': { assets: {}, liabilities: {} } } };
    Reflect.deleteProperty(partial.eth['0x1'], 'assets');
    expect(blockchainValue(partial, isAssetIgnored).toFixed()).toBe('0');
  });
});

describe('totalsByLocation', () => {
  it('should put the on-chain total under blockchain and add exchange and manual totals per location', () => {
    const totals = totalsByLocation(
      bigNumberify(250),
      [{ location: 'kraken', total: bigNumberify(10) }, { location: 'binance', total: bigNumberify(5) }],
      [{ location: 'kraken', value: bigNumberify(1) }, { location: 'blockchain', value: bigNumberify(2) }],
    );
    expect(plain(totals)).toEqual({ binance: '5', blockchain: '252', kraken: '11' });
  });
});

describe('totalsByChainLocation', () => {
  const chainOf: Record<string, string> = { ethereum: 'eth', optimism: 'optimism', polygon_pos: 'polygon' };

  it('should key each chain by the location standing for it and leave out chains holding nothing', () => {
    const totals = totalsByChainLocation(
      balances,
      ['ethereum', 'optimism', 'polygon_pos', 'kraken'],
      location => chainOf[location],
      isAssetIgnored,
    );
    expect(plain(totals)).toEqual({ ethereum: '250', optimism: '7' });
  });
});
