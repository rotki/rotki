import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

describe('useSupportedChains', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  describe('isEarlyIntegrationChain', () => {
    it('should return true for chains with limited protocol coverage', () => {
      const { isEarlyIntegrationChain } = useSupportedChains();
      expect(isEarlyIntegrationChain('avax')).toBe(true);
      expect(isEarlyIntegrationChain('hyperliquid')).toBe(true);
      expect(isEarlyIntegrationChain('monad')).toBe(true);
      expect(isEarlyIntegrationChain('sonic')).toBe(true);
      expect(isEarlyIntegrationChain('robinhood')).toBe(true);
    });

    it('should return false for fully supported or unknown chains', () => {
      const { isEarlyIntegrationChain } = useSupportedChains();
      expect(isEarlyIntegrationChain('eth')).toBe(false);
      expect(isEarlyIntegrationChain('ethereum')).toBe(false);
      expect(isEarlyIntegrationChain('solana')).toBe(false);
      expect(isEarlyIntegrationChain('')).toBe(false);
    });
  });
});
