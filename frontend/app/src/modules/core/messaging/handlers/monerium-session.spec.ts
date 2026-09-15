import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMoneriumSessionHandler } from '@/modules/core/messaging/handlers/monerium-session';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const mockRefreshStatus = vi.fn<() => Promise<void>>();
const mockSetStatus = vi.fn();

vi.mock('@/modules/integrations/monerium/use-monerium-auth', () => ({
  useMoneriumOAuth: vi.fn(() => ({
    refreshStatus: mockRefreshStatus,
    setStatus: mockSetStatus,
  })),
}));

describe('createMoneriumSessionHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockRefreshStatus.mockResolvedValue(undefined);
  });

  it('should raise the expired-session row and create no notification', async () => {
    const handler = createMoneriumSessionHandler();

    const result = await handler.handle({ error: 'session expired' });

    expect(result).toBeNull();
    expect(useRaisedConditionsStore().conditions).toEqual([{ kind: RaisedConditionKind.MONERIUM_SESSION }]);
  });

  it('should clear the local authentication state before refreshing it', async () => {
    const handler = createMoneriumSessionHandler();

    await handler.handle({ error: 'session expired' });

    expect(mockSetStatus).toHaveBeenCalledWith({ authenticated: false });
    expect(mockRefreshStatus).toHaveBeenCalledOnce();
    expect(mockSetStatus.mock.invocationCallOrder[0]).toBeLessThan(mockRefreshStatus.mock.invocationCallOrder[0]);
  });

  it('should keep the row raised when the status refresh fails', async () => {
    mockRefreshStatus.mockRejectedValue(new Error('offline'));
    const handler = createMoneriumSessionHandler();

    await handler.handle({ error: 'session expired' });

    expect(useRaisedConditionsStore().conditions).toEqual([{ kind: RaisedConditionKind.MONERIUM_SESSION }]);
  });
});
