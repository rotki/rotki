import { describe, expect, it, vi } from 'vitest';
import { getAccountFilterParams, useBlockchainAccountFilter } from './use-blockchain-account-filter';

vi.mock('@/modules/accounts/use-account-category-helper', async () => {
  const { ref } = await import('vue');
  return {
    useAccountCategoryHelper: (): { chainIds: Ref<string[]>; isEvm: Ref<boolean> } => ({
      chainIds: ref<string[]>([]),
      isEvm: ref<boolean>(true),
    }),
  };
});

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): { getAddressName: () => string | undefined } => ({
    getAddressName: (): string | undefined => undefined,
  }),
}));

vi.mock('@/modules/balances/blockchain/use-blockchain-account-data', async () => {
  const { ref } = await import('vue');
  return {
    useBlockchainAccountData: (): { getAccountsByCategory: () => Ref<never[]> } => ({
      getAccountsByCategory: (): Ref<never[]> => ref<never[]>([]),
    }),
  };
});

describe('composables/filters/blockchain-account', () => {
  describe('useBlockchainAccountFilter', () => {
    it('should have strictMatching enabled for account matcher', () => {
      const t = vi.fn().mockImplementation((key: string) => key);
      const { matchers } = useBlockchainAccountFilter(t, 'evm');

      const accountMatcher = get(matchers).find(m => m.key === 'account');
      expect(accountMatcher).toBeDefined();
      expect('string' in accountMatcher! && accountMatcher.strictMatching).toBe(true);
    });

    it('should not have strictMatching enabled for chain matcher', () => {
      const t = vi.fn().mockImplementation((key: string) => key);
      const { matchers } = useBlockchainAccountFilter(t, 'evm');

      const chainMatcher = get(matchers).find(m => m.key === 'chain');
      expect(chainMatcher).toBeDefined();
      expect(chainMatcher!).not.toHaveProperty('strictMatching');
    });
  });

  describe('getAccountFilterParams', () => {
    it('should return empty object for undefined value', () => {
      expect(getAccountFilterParams(undefined)).toEqual({});
    });

    it('should extract address and label from "label (address)" format', () => {
      const address = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045';
      const label = 'vitalik.eth';
      const input = `${label} (${address})`;

      expect(getAccountFilterParams(input)).toEqual({
        address,
        label,
      });
    });

    it('should handle label with special characters in "label (address)" format', () => {
      const address = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045';
      const label = 'My Account #1 - Main';
      const input = `${label} (${address})`;

      expect(getAccountFilterParams(input)).toEqual({
        address,
        label,
      });
    });

    it('should handle label with spaces in "label (address)" format', () => {
      const address = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045';
      const label = 'spaced label';
      const input = `${label} (${address})`;

      expect(getAccountFilterParams(input)).toEqual({
        address,
        label,
      });
    });

    it('should return same value for both address and label when plain string', () => {
      const plainAddress = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045';

      expect(getAccountFilterParams(plainAddress)).toEqual({
        address: plainAddress,
        label: plainAddress,
      });
    });

    it('should return same value for both address and label when plain label string', () => {
      const plainLabel = 'my-account-label';

      expect(getAccountFilterParams(plainLabel)).toEqual({
        address: plainLabel,
        label: plainLabel,
      });
    });

    it('should handle empty string', () => {
      expect(getAccountFilterParams('')).toEqual({});
    });

    it('should handle nested parentheses in label', () => {
      const address = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045';
      const label = 'Account (Main)';
      const input = `${label} (${address})`;

      // The regex should capture the outermost parentheses
      const result = getAccountFilterParams(input);
      expect(result.address).toBe(address);
      expect(result.label).toBe(label);
    });
  });
});
