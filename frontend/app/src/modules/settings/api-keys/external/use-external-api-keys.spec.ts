import type { ExternalServiceKeys } from '@/modules/integrations/types';
import { NotificationGroup } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockDelete, mockQuery, mockResetSchedule, mockSet, mockShow } = vi.hoisted(() => ({
  mockDelete: vi.fn(),
  mockQuery: vi.fn(),
  mockResetSchedule: vi.fn(),
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

vi.mock('@/modules/core/notifications/use-notification-cooldown', () => ({
  useNotificationCooldown: vi.fn(() => ({
    recordDisplay: vi.fn(),
    resetSchedule: mockResetSchedule,
    shouldSuppress: vi.fn(() => false),
  })),
}));

const keys: ExternalServiceKeys = {};

describe('useExternalApiKeys', () => {
  let api: Awaited<typeof import('@/modules/settings/api-keys/external/use-external-api-keys')>;

  beforeEach(async () => {
    setActivePinia(createPinia());
    mockDelete.mockReset().mockResolvedValue(keys);
    mockQuery.mockReset().mockResolvedValue(keys);
    mockSet.mockReset().mockResolvedValue(keys);
    mockResetSchedule.mockReset();
    mockShow.mockReset();

    // The composable is shared, so each case needs a fresh module instance to get its own state.
    vi.resetModules();
    api = await import('@/modules/settings/api-keys/external/use-external-api-keys');
  });

  /** The reset is scoped to one service, so run its predicate against a few group keys. */
  function resetTargets(): string[] {
    expect(mockResetSchedule).toHaveBeenCalledTimes(1);
    const predicate = mockResetSchedule.mock.calls[0][0];
    return [
      `${NotificationGroup.MISSING_API_KEY}:blockscout`,
      `${NotificationGroup.MISSING_API_KEY}:etherscan`,
      `${NotificationGroup.NO_AVAILABLE_INDEXERS}:optimism`,
    ].filter(group => predicate(group));
  }

  it('should let the missing-key warning interrupt again after a key is saved', async () => {
    const { save } = api.useExternalApiKeys();

    await save({ apiKey: 'new-key', name: 'blockscout' });

    expect(resetTargets()).toStrictEqual([`${NotificationGroup.MISSING_API_KEY}:blockscout`]);
  });

  it('should let the missing-key warning interrupt again after a key is deleted', async () => {
    const { confirmDelete } = api.useExternalApiKeys();

    confirmDelete('blockscout');
    await mockShow.mock.calls[0][1]();

    expect(resetTargets()).toStrictEqual([`${NotificationGroup.MISSING_API_KEY}:blockscout`]);
  });

  it('should not reset the schedule when saving the key fails', async () => {
    mockSet.mockRejectedValue(new Error('rejected'));
    const { save } = api.useExternalApiKeys();

    await save({ apiKey: 'new-key', name: 'blockscout' });

    expect(mockResetSchedule).not.toHaveBeenCalled();
  });

  it('should not reset the schedule when deleting the key fails', async () => {
    mockDelete.mockRejectedValue(new Error('rejected'));
    const { confirmDelete } = api.useExternalApiKeys();

    confirmDelete('blockscout');
    await mockShow.mock.calls[0][1]();

    expect(mockResetSchedule).not.toHaveBeenCalled();
  });

  it('should not reset the schedule merely for asking to delete a key', () => {
    const { confirmDelete } = api.useExternalApiKeys();

    confirmDelete('blockscout');

    expect(mockResetSchedule).not.toHaveBeenCalled();
  });
});
