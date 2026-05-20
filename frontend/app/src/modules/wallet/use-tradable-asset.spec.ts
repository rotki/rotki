import type { Balances } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify, Zero } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useTradableAsset } from './use-tradable-asset';

const supportedChainsForConnectedAccount = ref<string[]>(['eth', 'optimism']);
const getAssetPrice = vi.fn();
const isEvm = vi.fn();
const getNativeAsset = vi.fn();

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: vi.fn(() => ({ supportedChainsForConnectedAccount })),
}));

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: vi.fn(() => ({ getAssetPrice })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getNativeAsset, isEvm })),
}));

function seedBalances(data: Balances): void {
  const { balances } = storeToRefs(useBalancesStore());
  set(balances, data);
}

describe('useTradableAsset', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(supportedChainsForConnectedAccount, ['eth', 'optimism']);
    isEvm.mockImplementation((chain: string) => ['eth', 'optimism'].includes(chain));
    getNativeAsset.mockImplementation((chain: string) => (chain === 'eth' ? 'ETH' : 'OP'));
    getAssetPrice.mockReturnValue(undefined);
  });

  it('should return empty list when address has no balances', () => {
    seedBalances({});
    const { allOwnedAssets } = useTradableAsset(ref('0xabc'));
    expect(get(allOwnedAssets)).toEqual([]);
  });

  it('should skip non-evm chains and unsupported chains', () => {
    seedBalances({
      btc: { '0xabc': { assets: { BTC: { address: { amount: bigNumberify(1), value: Zero } } }, liabilities: {} } },
      eth: { '0xabc': { assets: { ETH: { address: { amount: bigNumberify(2), value: Zero } } }, liabilities: {} } },
      polygon: { '0xabc': { assets: { MATIC: { address: { amount: bigNumberify(3), value: Zero } } }, liabilities: {} } },
    });

    const { allOwnedAssets } = useTradableAsset(ref('0xabc'));
    const result = get(allOwnedAssets);

    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({ asset: 'ETH', chain: 'eth' });
  });

  it('should enhance owned assets with price and sort natives first', () => {
    seedBalances({
      eth: {
        '0xabc': {
          assets: {
            DAI: { address: { amount: bigNumberify(100), value: Zero } },
            ETH: { address: { amount: bigNumberify(2), value: Zero } },
          },
          liabilities: {},
        },
      },
      optimism: {
        '0xabc': {
          assets: {
            OP: { address: { amount: bigNumberify(5), value: Zero } },
          },
          liabilities: {},
        },
      },
    });

    getAssetPrice.mockImplementation((asset: string) => {
      if (asset === 'ETH')
        return bigNumberify(2000);
      if (asset === 'DAI')
        return bigNumberify(1);
      if (asset === 'OP')
        return bigNumberify(3);
      return undefined;
    });

    const { allOwnedAssets } = useTradableAsset(ref('0xabc'));
    const result = get(allOwnedAssets);

    expect(result).toHaveLength(3);
    expect(result[0].asset).toBe('ETH');
    expect(result[0].fiatValue?.toString()).toBe('4000');
    expect(result[1].asset).toBe('OP');
    expect(result[2].asset).toBe('DAI');
    expect(result[2].price?.toString()).toBe('1');
  });

  it('should leave price/fiatValue undefined when price is missing or non-positive', () => {
    seedBalances({
      eth: {
        '0xabc': {
          assets: {
            FOO: { address: { amount: bigNumberify(10), value: Zero } },
          },
          liabilities: {},
        },
      },
    });

    getAssetPrice.mockImplementation((asset: string) => (asset === 'FOO' ? Zero : undefined));

    const { allOwnedAssets } = useTradableAsset(ref('0xabc'));
    const [item] = get(allOwnedAssets);

    expect(item.asset).toBe('FOO');
    expect(item.fiatValue).toBeUndefined();
    expect(item.price).toBeUndefined();
  });

  it('should deduplicate assets across addresses when no address is given and skip price enhancement', () => {
    seedBalances({
      eth: {
        '0xa': { assets: { ETH: { address: { amount: bigNumberify(1), value: Zero } } }, liabilities: {} },
        '0xb': { assets: { ETH: { address: { amount: bigNumberify(2), value: Zero } } }, liabilities: {} },
      },
    });

    const { allOwnedAssets } = useTradableAsset(ref(undefined));
    const result = get(allOwnedAssets);

    expect(result).toHaveLength(1);
    expect(result[0].asset).toBe('ETH');
    expect(result[0].amount.isZero()).toBe(true);
    expect(getAssetPrice).not.toHaveBeenCalled();
  });

  it('should skip address entries without an assets bag', () => {
    seedBalances({
      eth: {
        '0xabc': { assets: {}, liabilities: {} },
      },
    });

    const { allOwnedAssets } = useTradableAsset(ref('0xabc'));
    expect(get(allOwnedAssets)).toEqual([]);
  });

  it('should expose getAssetDetail that matches by asset+chain', () => {
    seedBalances({
      eth: {
        '0xabc': {
          assets: {
            ETH: { address: { amount: bigNumberify(2), value: Zero } },
            DAI: { address: { amount: bigNumberify(50), value: Zero } },
          },
          liabilities: {},
        },
      },
    });
    getAssetPrice.mockReturnValue(bigNumberify(1));

    const { getAssetDetail } = useTradableAsset(ref('0xabc'));

    expect(get(getAssetDetail('DAI', 'eth'))?.asset).toBe('DAI');
    expect(get(getAssetDetail('UNKNOWN', 'eth'))).toBeUndefined();
  });
});
