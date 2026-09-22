import type { ExternalServiceKeys } from '@/modules/integrations/types';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockDelete, mockQuery, mockSet, mockShow } = vi.hoisted(() => ({
  mockDelete: vi.fn(),
  mockQuery: vi.fn(),
  mockSet: vi.fn(),
  mockShow: vi.fn(),
}));

vi.mock('@/modules/settings/api/use-external-services-api', () => ({
  useExternalServicesApi: vi.fn(() => ({
    deleteExternalServices: mockDelete,
    queryExternalServices: mockQuery,
    setExternalServices: mockSet,
  })),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: vi.fn(() => ({ show: mockShow })),
}));

const withBlockscout: ExternalServiceKeys = { blockscout: { apiKey: 'new-key' } };

describe('useExternalApiKeys', () => {
  let api: Awaited<typeof import('@/modules/settings/api-keys/external/use-external-api-keys')>;

  beforeEach(async () => {
    setActivePinia(createPinia());
    mockDelete.mockReset().mockResolvedValue({});
    mockQuery.mockReset().mockResolvedValue({});
    mockSet.mockReset().mockResolvedValue(withBlockscout);
    mockShow.mockReset();

    // The composable is shared, so each case needs a fresh module instance to get its own state.
    vi.resetModules();
    api = await import('@/modules/settings/api-keys/external/use-external-api-keys');
  });

  it('should expose a saved key, which is what takes down its missing-key row', async () => {
    const { getApiKey, save } = api.useExternalApiKeys();

    await save({ apiKey: 'new-key', name: 'blockscout' });

    expect(getApiKey('blockscout')).toBe('new-key');
  });

  describe('the chain rows that asked for a paid Etherscan key', () => {
    let conditions: Awaited<typeof import('@/modules/shell/action-center/use-raised-conditions-store')>;

    beforeEach(async () => {
      conditions = await import('@/modules/shell/action-center/use-raised-conditions-store');
      const { raise } = conditions.useRaisedConditionsStore();
      raise({ chain: 'base', kind: conditions.RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: true });
      raise({ chain: 'optimism', kind: conditions.RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: false });
    });

    function raisedChains(): string[] {
      return get(conditions.useRaisedConditionsStore().conditions).flatMap(condition => 'chain' in condition ? [condition.chain] : []);
    }

    it('should come down when an Etherscan key is saved, leaving the chains that asked for no key', async () => {
      await api.useExternalApiKeys().save({ apiKey: 'paid-key', name: 'etherscan' });

      expect(raisedChains()).toEqual(['optimism']);
    });

    it('should stay when another service\'s key is saved', async () => {
      await api.useExternalApiKeys().save({ apiKey: 'new-key', name: 'blockscout' });

      expect(raisedChains()).toEqual(['base', 'optimism']);
    });

    it('should stay when saving the Etherscan key fails', async () => {
      mockSet.mockRejectedValue(new Error('rejected'));

      await api.useExternalApiKeys().save({ apiKey: 'paid-key', name: 'etherscan' });

      expect(raisedChains()).toEqual(['base', 'optimism']);
    });
  });

  it('should keep the key unchanged and report the error when saving fails', async () => {
    mockSet.mockRejectedValue(new Error('rejected'));
    const { actionStatus, getApiKey, save } = api.useExternalApiKeys();

    await save({ apiKey: 'new-key', name: 'blockscout' });

    expect(getApiKey('blockscout')).toBe('');
    expect(get(actionStatus('blockscout'))?.success).toBeFalsy();
  });

  it('should ask before deleting a key, and delete it only once confirmed', async () => {
    const { confirmDelete, getApiKey, save } = api.useExternalApiKeys();
    await save({ apiKey: 'new-key', name: 'blockscout' });

    confirmDelete('blockscout');
    expect(mockDelete).not.toHaveBeenCalled();

    await mockShow.mock.calls[0][1]();

    expect(mockDelete).toHaveBeenCalledWith('blockscout');
    expect(getApiKey('blockscout')).toBe('');
  });
});
