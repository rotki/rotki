import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { createTestBalance, createTestManualBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { fromBlockchain, fromExchanges, fromManual } from './sources';

function plain(value: unknown): unknown {
  return JSON.parse(JSON.stringify(value));
}

const balances: Balances = {
  eth: {
    '0x1234': {
      assets: {
        ETH: { 'address': createTestBalance(1, 100), 'uniswap-v3': createTestBalance(1, 100) },
      },
      liabilities: { DAI: { makerdao: createTestBalance(5, 5) } },
    },
    '0x5678': {
      assets: { ETH: { address: createTestBalance(4, 400) } },
      liabilities: {},
    },
  },
  polygon: {
    '0x1234': {
      assets: {
        ETH: { 'address': createTestBalance(2, 200), 'uniswap-v3': createTestBalance(2, 200) },
      },
      liabilities: {},
    },
  },
};

describe('fromBlockchain', () => {
  it('should sum an asset across accounts and chains, keeping the per-chain split for the address protocol', () => {
    expect(plain(fromBlockchain(balances).ETH.address)).toEqual({
      amount: '7',
      chains: { eth: { amount: '5', value: '500' }, polygon: { amount: '2', value: '200' } },
      value: '700',
    });
  });

  it('should add a per-chain split even when there is only one chain', () => {
    const result = fromBlockchain(balances, { chains: ['polygon'] });
    expect(plain(result.ETH.address.chains)).toEqual({ polygon: { amount: '2', value: '200' } });
  });

  it('should not add a per-chain split to other protocols', () => {
    const uniswap = fromBlockchain(balances).ETH['uniswap-v3'];
    expect(uniswap.amount.toFixed()).toBe('3');
    expect(uniswap.chains).toBeUndefined();
  });

  it('should read only the requested chains, treating an empty list as every chain', () => {
    expect(fromBlockchain(balances, { chains: ['eth'] }).ETH.address.amount.toFixed()).toBe('5');
    expect(fromBlockchain(balances, { chains: [] }).ETH.address.amount.toFixed()).toBe('7');
  });

  it('should read only the requested account', () => {
    expect(fromBlockchain(balances, { address: '0x5678' }).ETH.address.amount.toFixed()).toBe('4');
  });

  it('should read liabilities when asked', () => {
    const result = fromBlockchain(balances, { key: 'liabilities' });
    expect(Object.keys(result)).toEqual(['DAI']);
    expect(result.DAI.makerdao.amount.toFixed()).toBe('5');
  });
});

describe('fromExchanges', () => {
  const exchangeBalances = {
    binance: { BTC: createTestBalance(2, 20), ETH: createTestBalance(1, 10) },
    kraken: { BTC: createTestBalance(1, 10) },
  };

  it('should key each asset by the exchange that holds it', () => {
    expect(plain(fromExchanges(exchangeBalances))).toEqual({
      BTC: { binance: { amount: '2', value: '20' }, kraken: { amount: '1', value: '10' } },
      ETH: { binance: { amount: '1', value: '10' } },
    });
  });

  it('should read only the requested exchange', () => {
    expect(Object.keys(fromExchanges(exchangeBalances, 'kraken'))).toEqual(['BTC']);
  });
});

describe('fromManual', () => {
  const manual: ManualBalanceWithValue[] = [
    createTestManualBalance('BTC', 1, 10, 'kraken', BalanceType.ASSET, 1),
    createTestManualBalance('BTC', 2, 20, 'kraken', BalanceType.ASSET, 2),
    createTestManualBalance('BTC', 4, 40, 'external', BalanceType.ASSET, 3),
  ];

  it('should sum balances of one asset at one location and mark them manual', () => {
    expect(plain(fromManual(manual))).toEqual({
      BTC: {
        external: { amount: '4', containsManual: true, value: '40' },
        kraken: { amount: '3', containsManual: true, value: '30' },
      },
    });
  });
});
