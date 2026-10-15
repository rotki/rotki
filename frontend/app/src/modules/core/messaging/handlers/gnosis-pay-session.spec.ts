// Seam: the handler turns the backend's sign in request into a notification whose title and
// action label depend on whether the user's session expired or they never connected, and
// whose action opens the Gnosis Pay entry of the external services page.
import type { Router } from 'vue-router';
import { assert, NotificationGroup, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createGnosisPaySessionHandler } from '@/modules/core/messaging/handlers/gnosis-pay-session';

const mockPush = vi.fn();

const router = createMock<Router>({ push: mockPush });

describe('createGnosisPaySessionHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should title an expired session as expired and offer to re-authenticate', async () => {
    const handler = createGnosisPaySessionHandler(mockT, router);
    const result = await handler.handle({ error: 'session expired', reason: 'expired', reminder: false });

    assert(result);
    expect(result.title).toBe('notification_messages.gnosis_pay_session_key_expired.title');
    expect(result.action).toMatchObject({ label: 'external_services.actions.reauthenticate' });
    expect(result.message).toBe('session expired');
    expect(result.severity).toBe(Severity.WARNING);
    expect(result.group).toBe(NotificationGroup.GNOSIS_PAY_SESSION_EXPIRED);
  });

  it('should title a user who never connected as not connected and offer to authenticate', async () => {
    const handler = createGnosisPaySessionHandler(mockT, router);
    const result = await handler.handle({ error: 'sign in', reason: 'not_connected', reminder: true });

    assert(result);
    expect(result.title).toBe('notification_messages.gnosis_pay_not_connected.title');
    expect(result.action).toMatchObject({ label: 'external_services.actions.authenticate' });
    expect(result.message).toBe('sign in');
    expect(result.group).toBe(`${NotificationGroup.INTEGRATION_SIGN_IN_REMINDER}:gnosis_pay`);
  });

  it('should nag an expired session on the schedule when redecoding repeats it', async () => {
    const handler = createGnosisPaySessionHandler(mockT, router);
    const result = await handler.handle({ error: 'sign in again', reason: 'expired', reminder: true });

    assert(result);
    expect(result.title).toBe('notification_messages.gnosis_pay_session_key_expired.title');
    expect(result.group).toBe(`${NotificationGroup.INTEGRATION_SIGN_IN_REMINDER}:gnosis_pay`);
  });

  it('should open the Gnosis Pay entry of the external services page', async () => {
    const handler = createGnosisPaySessionHandler(mockT, router);
    const result = await handler.handle({ error: 'sign in', reason: 'not_connected', reminder: true });

    assert(result);
    assert(result.action && !Array.isArray(result.action));
    await result.action.action();
    expect(mockPush).toHaveBeenCalledWith({
      name: '/api-keys/external/',
      query: { service: 'gnosis_pay' },
    });
  });
});
