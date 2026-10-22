import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMoneriumSessionHandler } from '@/modules/core/messaging/handlers/monerium-session';
import { RaisedConditionKind, SessionCause, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const mockRefreshStatus = vi.fn<() => Promise<void>>();
const mockSetStatus = vi.fn();

vi.mock('@/modules/integrations/monerium/use-monerium-auth', () => ({
  useMoneriumOAuth: vi.fn(() => ({
    refreshStatus: mockRefreshStatus,
    setStatus: mockSetStatus,
  })),
}));

const expiry = { error: 'session expired', reason: 'expired', reminder: false } as const;

describe('createMoneriumSessionHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockRefreshStatus.mockResolvedValue(undefined);
  });

  it('should raise the expired-session row and create no notification', async () => {
    const handler = createMoneriumSessionHandler();

    const result = await handler.handle(expiry);

    expect(result).toBeNull();
    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause: SessionCause.EXPIRED, kind: RaisedConditionKind.MONERIUM_SESSION },
    ]);
  });

  it('should clear the local authentication state before refreshing it', async () => {
    const handler = createMoneriumSessionHandler();

    await handler.handle(expiry);

    expect(mockSetStatus).toHaveBeenCalledWith({ authenticated: false });
    expect(mockRefreshStatus).toHaveBeenCalledOnce();
    expect(mockSetStatus.mock.invocationCallOrder[0]).toBeLessThan(mockRefreshStatus.mock.invocationCallOrder[0]);
  });

  it('should keep the row raised when the status refresh fails', async () => {
    mockRefreshStatus.mockRejectedValue(new Error('offline'));
    const handler = createMoneriumSessionHandler();

    await handler.handle(expiry);

    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause: SessionCause.EXPIRED, kind: RaisedConditionKind.MONERIUM_SESSION },
    ]);
  });

  it('should only raise the row for a reminder, since the user is already signed out', async () => {
    const handler = createMoneriumSessionHandler();

    await handler.handle({ error: 'sign in', reason: 'expired', reminder: true });

    expect(mockSetStatus).not.toHaveBeenCalled();
    expect(mockRefreshStatus).not.toHaveBeenCalled();
    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause: SessionCause.EXPIRED, kind: RaisedConditionKind.MONERIUM_SESSION },
    ]);
  });

  it('should raise the row as not connected for a user who never signed in', async () => {
    const handler = createMoneriumSessionHandler();

    await handler.handle({ error: 'not connected', reason: 'not_connected', reminder: true });

    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause: SessionCause.NOT_CONNECTED, kind: RaisedConditionKind.MONERIUM_SESSION },
    ]);
  });
});
