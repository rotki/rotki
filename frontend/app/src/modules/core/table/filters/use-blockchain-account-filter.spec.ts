import { describe, expect, it, vi } from 'vitest';
import { useBlockchainAccountFilter } from './use-blockchain-account-filter';

vi.mock('@/modules/accounts/use-account-category-helper', async () => {
  const { ref } = await import('vue');
  return {
    useAccountCategoryHelper: (): { chainIds: Ref<string[]>; isEvm: Ref<boolean> } => ({
      chainIds: ref<string[]>(['eth', 'optimism']),
      isEvm: ref<boolean>(true),
    }),
  };
});

describe('composables/filters/blockchain-account', () => {
  describe('useBlockchainAccountFilter', () => {
    it('should offer the chain matcher alone', () => {
      const t = vi.fn().mockImplementation((key: string) => key);
      const { matchers } = useBlockchainAccountFilter(t, 'evm');

      // The account filter is a param-bound pill built from the account list, not a matcher.
      expect(get(matchers).map(matcher => matcher.key)).toStrictEqual(['chain']);
    });

    it('should not have strictMatching enabled for chain matcher', () => {
      const t = vi.fn().mockImplementation((key: string) => key);
      const { matchers } = useBlockchainAccountFilter(t, 'evm');

      const chainMatcher = get(matchers).find(m => m.key === 'chain');
      expect(chainMatcher).toBeDefined();
      expect(chainMatcher!).not.toHaveProperty('strictMatching');
    });

    it('should accept a known chain and reject an unknown one', () => {
      const t = vi.fn().mockImplementation((key: string) => key);
      const { matchers } = useBlockchainAccountFilter(t, 'evm');

      const chainMatcher = get(matchers).find(m => m.key === 'chain');
      expect('string' in chainMatcher! && chainMatcher.validate('optimism')).toBe(true);
      expect('string' in chainMatcher! && chainMatcher.validate('nope')).toBe(false);
    });
  });
});
