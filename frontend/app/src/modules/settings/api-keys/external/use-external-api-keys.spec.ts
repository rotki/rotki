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
