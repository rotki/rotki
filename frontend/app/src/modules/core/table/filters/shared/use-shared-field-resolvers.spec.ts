import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const ADDRESS = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045';

describe('useSharedFieldResolvers', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  function setScramble(scrambleData: boolean): void {
    useSettingsRepo().updateFrontend({ scrambleData, scrambleMultiplier: 3.5 });
  }

  // A filtered address must be no more revealing than the same address anywhere else in the app,
  // and the pill is the one place it is shown back to the user in full context.
  describe('privacy mode', () => {
    it('should shorten an address without altering it while privacy is off', () => {
      setScramble(false);
      const { resolveHex } = useSharedFieldResolvers();

      const shown = resolveHex(ADDRESS);

      expect(shown).toBe('0xd8dA...6045');
      expect(ADDRESS.startsWith(shown.split('...')[0])).toBe(true);
    });

    it('should scramble an address once privacy is on', () => {
      setScramble(true);
      const { resolveHex } = useSharedFieldResolvers();

      const shown = resolveHex(ADDRESS);

      // Still an address-shaped, shortened value, but not this address: neither end survives.
      expect(shown).toMatch(/^0x\w{4}\.\.\.\w{4}$/);
      expect(shown).not.toBe('0xd8dA...6045');
      expect(ADDRESS).not.toContain(shown.slice(-4));
    });

    // The same resolver backs the transaction-hash field, whose values are just as identifying.
    it('should scramble a transaction hash too', () => {
      const hash = `0x${'ab'.repeat(32)}`;
      setScramble(true);
      const { resolveHex } = useSharedFieldResolvers();

      expect(resolveHex(hash)).not.toBe('0xabab...abab');
    });
  });

  it('should fall back to a shortened address for an asset with no metadata', () => {
    setScramble(false);
    const { resolveAssetSymbol } = useSharedFieldResolvers();

    // Nothing is cached for it, so the resolver hands back the `EVM Token: 0x…` stand-in, which is
    // no more readable on a pill than the raw identifier was.
    const shown = resolveAssetSymbol('eip155:1/erc20:0x214AF1443f6bB9FFB2bDcF301c762Df28Dd7f818');

    expect(shown).toBe('0x214A...f818');
  });
});
