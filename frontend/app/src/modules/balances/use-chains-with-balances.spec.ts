import type { AssetProtocolBalances } from '@/modules/balances/types/blockchain-balances';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useChainsWithBalances } from '@/modules/balances/use-chains-with-balances';

function held(asset: string): AssetProtocolBalances {
  return { [asset]: { address: { amount: bigNumberify(1), value: bigNumberify(1) } } };
}

describe('useChainsWithBalances', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const { updateBalances } = useBalancesStore();
    const totals = { assets: {}, liabilities: {} };
    updateBalances('eth', { perAccount: { eth: {
      '0xaddress1': { assets: held('ETH'), liabilities: {} },
      '0xother': { assets: held('GNO'), liabilities: {} },
    } }, totals });
    updateBalances('optimism', { perAccount: { optimism: { '0xaddress1': { assets: held('BTC'), liabilities: {} } } }, totals });
    updateBalances('base', { perAccount: { base: { '0xaddress1': { assets: {}, liabilities: held('DAI') } } }, totals });
    updateBalances('gnosis', { perAccount: { gnosis: { '0xother': { assets: held('GNO'), liabilities: {} } } }, totals });
  });

  it('should keep the given chains where the group holds assets or owes liabilities, in the order given', () => {
    expect(get(useChainsWithBalances('0xaddress1', ['optimism', 'gnosis', 'base', 'eth']))).toStrictEqual(['optimism', 'base', 'eth']);
  });

  it('should only look at the chains it is given', () => {
    expect(get(useChainsWithBalances('0xaddress1', ['eth']))).toStrictEqual(['eth']);
  });

  it('should not count a chain where the group holds only ignored assets', () => {
    useAssetsStore().ignoredAssets.push('BTC');

    expect(get(useChainsWithBalances('0xaddress1', ['eth', 'optimism', 'base']))).toStrictEqual(['eth', 'base']);
  });

  it('should list nothing without a group', () => {
    expect(get(useChainsWithBalances(undefined, ['eth', 'gnosis']))).toStrictEqual([]);
  });
});
