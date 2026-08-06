import { beforeEach, describe, expect, it } from 'vitest';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useDisabledChains } from './use-disabled-chains';

describe('useDisabledChains', () => {
  const ETH_ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
  const OTHER_ETH_ADDRESS = '0x71C7656EC7ab88b098defB751B7401B5f6d8976F';

  let composable: ReturnType<typeof useDisabledChains>;

  function setDisabled(value: Record<string, string[]>): void {
    const store = useSettingsRepo();
    store.updateGeneral({ ...store.general, disabledChainQueries: value });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    composable = useDisabledChains();
  });

  describe('isChainExcluded', () => {
    it('should be false for a chain with no rule', () => {
      expect(composable.isChainExcluded('eth')).toBe(false);
    });

    it('should be true only for the empty-array rule that disables the whole chain', () => {
      setDisabled({ eth: [] });
      expect(composable.isChainExcluded('eth')).toBe(true);
    });

    it('should be false when only some addresses on the chain are excluded', () => {
      setDisabled({ eth: [ETH_ADDRESS] });
      expect(composable.isChainExcluded('eth')).toBe(false);
    });

    it('should match the chain id regardless of case', () => {
      setDisabled({ polygon_pos: [] });
      expect(composable.isChainExcluded('POLYGON_POS')).toBe(true);
    });
  });

  describe('isAddressExcluded', () => {
    it('should be false when the chain has no rule', () => {
      expect(composable.isAddressExcluded('eth', ETH_ADDRESS)).toBe(false);
    });

    it('should be true for every address once the whole chain is disabled', () => {
      setDisabled({ eth: [] });
      expect(composable.isAddressExcluded('eth', ETH_ADDRESS)).toBe(true);
      expect(composable.isAddressExcluded('eth', OTHER_ETH_ADDRESS)).toBe(true);
    });

    it('should be true only for the listed addresses on a partially disabled chain', () => {
      setDisabled({ eth: [ETH_ADDRESS] });
      expect(composable.isAddressExcluded('eth', ETH_ADDRESS)).toBe(true);
      expect(composable.isAddressExcluded('eth', OTHER_ETH_ADDRESS)).toBe(false);
    });

    it('should match an address that differs only by case', () => {
      // The setting is written from tracked accounts while the sync panel's addresses arrive over
      // the websocket, so a case-only difference must not silently defeat the rule.
      setDisabled({ eth: [ETH_ADDRESS.toLowerCase()] });
      expect(composable.isAddressExcluded('eth', ETH_ADDRESS)).toBe(true);
    });
  });

  describe('filterAccounts', () => {
    const sample = [
      { address: ETH_ADDRESS, chain: 'eth' },
      { address: OTHER_ETH_ADDRESS, chain: 'eth' },
      { address: '0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199', chain: 'optimism' },
      { address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'btc' },
    ];

    it('should return the input unchanged when nothing is disabled', () => {
      expect(composable.filterAccounts(sample)).toEqual(sample);
    });

    it('should combine full-chain and per-address rules', () => {
      setDisabled({ eth: [ETH_ADDRESS], optimism: [] });
      expect(composable.filterAccounts(sample)).toEqual([
        { address: OTHER_ETH_ADDRESS, chain: 'eth' },
        { address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'btc' },
      ]);
    });

    it('should preserve extra properties on the accounts it keeps', () => {
      setDisabled({ eth: [] });
      const withExtras = [
        { address: ETH_ADDRESS, chain: 'eth', status: 'querying' },
        { address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'btc', status: 'complete' },
      ];
      expect(composable.filterAccounts(withExtras)).toEqual([
        { address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'btc', status: 'complete' },
      ]);
    });

    it('should react to the setting changing', () => {
      expect(composable.filterAccounts(sample)).toHaveLength(4);
      setDisabled({ eth: [] });
      expect(composable.filterAccounts(sample)).toHaveLength(2);
    });
  });
});
