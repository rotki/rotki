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
    const result = await handler.handle({ error: 'session expired', reason: 'expired', reminder: false });

    assert(result);
    expect(result.category).toBe(NotificationCategory.DEFAULT);
    expect(result.severity).toBe(Severity.WARNING);
    expect(result.message).toBe('session expired');
    expect(result.display).toBe(true);
  });

  it('should title an expired session as expired and offer to re-authenticate', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    const result = await handler.handle({ error: 'session expired', reason: 'expired', reminder: false });

    assert(result);
    expect(result.title).toBe('notification_messages.monerium_session_key_expired.title');
    expect(result.action).toMatchObject({ label: 'external_services.actions.reauthenticate' });
  });

  it('should title a user who never connected as not connected and offer to authenticate', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    const result = await handler.handle({ error: 'sign in', reason: 'not_connected', reminder: true });

    assert(result);
    expect(result.title).toBe('notification_messages.monerium_not_connected.title');
    expect(result.action).toMatchObject({ label: 'external_services.actions.authenticate' });
    expect(result.message).toBe('sign in');
  });

  it('should share the group of the authentication flow, so a re-authentication replaces it', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    const result = await handler.handle({ error: 'session expired', reason: 'expired', reminder: false });

    assert(result);
    expect(result.group).toBe(NotificationGroup.MONERIUM_AUTH);
  });

  it('should clear the local authentication state before notifying', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    await handler.handle({ error: 'session expired', reason: 'expired', reminder: false });

    expect(mockSetStatus).toHaveBeenCalledWith({ authenticated: false });
    expect(mockRefreshStatus).toHaveBeenCalledOnce();
  });

  it('should nag a user who never connected on the integration schedule', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    const result = await handler.handle({ error: 'sign in', reason: 'not_connected', reminder: true });

    assert(result);
    expect(result.group).toBe(`${NotificationGroup.INTEGRATION_SIGN_IN_REMINDER}:monerium`);
  });

  it('should not touch the authentication state of a user who never connected', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    await handler.handle({ error: 'sign in', reason: 'not_connected', reminder: true });

    expect(mockSetStatus).not.toHaveBeenCalled();
    expect(mockRefreshStatus).not.toHaveBeenCalled();
  });

  it('should nag an expired session on the schedule when redecoding repeats it', async () => {
    const handler = createMoneriumSessionHandler(mockT, router);
    const result = await handler.handle({ error: 'sign in again', reason: 'expired', reminder: true });

    assert(result);
    expect(result.title).toBe('notification_messages.monerium_session_key_expired.title');
    expect(result.group).toBe(`${NotificationGroup.INTEGRATION_SIGN_IN_REMINDER}:monerium`);
    expect(mockSetStatus).not.toHaveBeenCalled();
    expect(mockRefreshStatus).not.toHaveBeenCalled();
  });
});
