import type { ExternalServiceKeys } from '@/modules/integrations/types';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockDelete, mockQuery, mockSet } = vi.hoisted(() => ({
  mockDelete: vi.fn(),
  mockQuery: vi.fn(),
  mockSet: vi.fn(),
}));

vi.mock('@/modules/settings/api/use-external-services-api', () => ({
  useExternalServicesApi: vi.fn(() => ({
    deleteExternalServices: mockDelete,
    queryExternalServices: mockQuery,
    setExternalServices: mockSet,
  })),
}));

const withBlockscout: ExternalServiceKeys = { blockscout: { apiKey: 'new-key' } };

describe('useExternalApiKeys', () => {
  let api: Awaited<typeof import('@/modules/settings/api-keys/external/use-external-api-keys')>;

  beforeEach(async () => {
    setActivePinia(createPinia());
    mockDelete.mockReset().mockResolvedValue({});
    mockQuery.mockReset().mockResolvedValue({});
    mockSet.mockReset().mockResolvedValue(withBlockscout);

    // The composable is shared, so each case needs a fresh module instance to get its own state.
    vi.resetModules();
    api = await import('@/modules/settings/api-keys/external/use-external-api-keys');
  });

  it('should expose a saved key, which is what takes down its missing-key row', async () => {
    const { getApiKey, save } = api.useExternalApiKeys();

    await save({ apiKey: 'new-key', name: 'blockscout' });

    expect(getApiKey('blockscout')).toBe('new-key');
  });

  describe('the rows that asked for a key', () => {
    let conditions: Awaited<typeof import('@/modules/shell/action-center/use-raised-conditions-store')>;

    beforeEach(async () => {
      conditions = await import('@/modules/shell/action-center/use-raised-conditions-store');
      const { NoIndexersCause, RaisedConditionKind, useRaisedConditionsStore } = conditions;
      const { raise } = useRaisedConditionsStore();
      raise({ cause: NoIndexersCause.PAID_ETHERSCAN_KEY, chain: 'base', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS });
      raise({ cause: NoIndexersCause.BLOCKSCOUT_OR_PAID_ETHERSCAN_KEY, chain: 'gnosis', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS });
      raise({ cause: NoIndexersCause.UNAVAILABLE, chain: 'optimism', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS });
      raise({ keyRejected: true, kind: RaisedConditionKind.MISSING_API_KEY, location: 'Base', service: 'blockscout' });
    });

    function raised(): string[] {
      return get(conditions.useRaisedConditionsStore().conditions).flatMap((condition) => {
        if ('chain' in condition)
          return [condition.chain];
        return 'service' in condition ? [condition.service] : [];
      });
    }

    it('should take down every chain an Etherscan key restores, leaving the chains that asked for no key', async () => {
      await api.useExternalApiKeys().save({ apiKey: 'paid-key', name: 'etherscan' });

      expect(raised()).toEqual(['optimism', 'blockscout']);
    });

    it('should take down the chains a Blockscout key restores and its refused key', async () => {
      await api.useExternalApiKeys().save({ apiKey: 'new-key', name: 'blockscout' });

      expect(raised()).toEqual(['base', 'optimism']);
    });

    it('should take down a refused key when the key is deleted, leaving the chains that ask for one', async () => {
      await api.useExternalApiKeys().deleteService('blockscout');

      expect(raised()).toEqual(['base', 'gnosis', 'optimism']);
    });

    it('should stay when another service\'s key is saved', async () => {
      await api.useExternalApiKeys().save({ apiKey: 'new-key', name: 'helius' });

      expect(raised()).toEqual(['base', 'gnosis', 'optimism', 'blockscout']);
    });

    it('should stay when saving the Etherscan key fails', async () => {
      mockSet.mockRejectedValue(new Error('rejected'));

      await api.useExternalApiKeys().save({ apiKey: 'paid-key', name: 'etherscan' });

      expect(raised()).toEqual(['base', 'gnosis', 'optimism', 'blockscout']);
    });
  });

  it('should keep the key unchanged and report the error when saving fails', async () => {
    mockSet.mockRejectedValue(new Error('rejected'));
    const { actionStatus, getApiKey, save } = api.useExternalApiKeys();

    await save({ apiKey: 'new-key', name: 'blockscout' });

    expect(getApiKey('blockscout')).toBe('');
    expect(get(actionStatus('blockscout'))?.success).toBeFalsy();
  });

  it('should delete a key, the card having asked already', async () => {
    const { deleteService, getApiKey, save } = api.useExternalApiKeys();
    await save({ apiKey: 'new-key', name: 'blockscout' });

    await deleteService('blockscout');

    expect(mockDelete).toHaveBeenCalledWith('blockscout');
    expect(getApiKey('blockscout')).toBe('');
  });

  it('should keep the key and report the error when deleting fails', async () => {
    mockDelete.mockRejectedValue(new Error('rejected'));
    const { actionStatus, deleteService, getApiKey, save } = api.useExternalApiKeys();
    await save({ apiKey: 'new-key', name: 'blockscout' });

    await deleteService('blockscout');

    expect(getApiKey('blockscout')).toBe('new-key');
    expect(get(actionStatus('blockscout'))?.message).toContain('external_services.delete_error.description');
  });
});
