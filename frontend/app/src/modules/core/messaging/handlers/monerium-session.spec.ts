import type { Router } from 'vue-router';
import { assert, NotificationCategory, NotificationGroup, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMoneriumSessionHandler } from '@/modules/core/messaging/handlers/monerium-session';

const mockRefreshStatus = vi.fn();
const mockSetStatus = vi.fn();
const mockPush = vi.fn();

vi.mock('@/modules/integrations/monerium/use-monerium-auth', () => ({
  useMoneriumOAuth: vi.fn(() => ({
    refreshStatus: mockRefreshStatus,
    setStatus: mockSetStatus,
  })),
}));

const router = createMock<Router>({ push: mockPush });

describe('createMoneriumSessionHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRefreshStatus.mockResolvedValue(undefined);
  });

  it('should build a warning notification with a re-authenticate action', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    const result = await handler.handle({ error: 'session expired' });

    assert(result);
    expect(result.category).toBe(NotificationCategory.DEFAULT);
    expect(result.severity).toBe(Severity.WARNING);
    expect(result.message).toBe('session expired');
    expect(result.display).toBe(true);
  });

  it('should share the group of the authentication flow, so a re-authentication replaces it', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    const result = await handler.handle({ error: 'session expired' });

    assert(result);
    expect(result.group).toBe(NotificationGroup.MONERIUM_AUTH);
  });

  it('should clear the local authentication state before notifying', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    await handler.handle({ error: 'session expired' });

    expect(mockSetStatus).toHaveBeenCalledWith({ authenticated: false });
    expect(mockRefreshStatus).toHaveBeenCalledOnce();
  });
});
