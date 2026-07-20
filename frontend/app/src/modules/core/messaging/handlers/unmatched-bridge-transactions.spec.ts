import type { Router } from 'vue-router';
import { NotificationCategory, NotificationGroup, Priority, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { assert, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { createUnmatchedBridgeTransactionsHandler } from '@/modules/core/messaging/handlers/unmatched-bridge-transactions';

const { removeMatching } = vi.hoisted(() => ({
  removeMatching: vi.fn<(predicate: (n: { group?: string }) => boolean) => void>(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ removeMatching }),
}));

interface RouterMock extends Pick<Router, 'currentRoute'> {
  push: Mock<Router['push']>;
}

function createRouter(routeName: string): RouterMock {
  return {
    // @ts-expect-error partial route mock - only the name is read by the handler
    currentRoute: ref({ name: routeName }),
    push: vi.fn<Router['push']>(),
  };
}

describe('createUnmatchedBridgeTransactionsHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should clear stale grouped notifications on every message', async () => {
    const handler = createUnmatchedBridgeTransactionsHandler(mockT, createRouter('/dashboard'));

    await handler.handle({ count: 0 });

    expect(removeMatching).toHaveBeenCalledTimes(1);
    const [predicate] = removeMatching.mock.calls[0];
    expect(predicate({ group: NotificationGroup.UNMATCHED_BRIDGE_TRANSACTIONS })).toBe(true);
    expect(predicate({ group: NotificationGroup.UNMATCHED_ASSET_MOVEMENTS })).toBe(false);
  });

  it('should return null when the count is zero', async () => {
    const handler = createUnmatchedBridgeTransactionsHandler(mockT, createRouter('/dashboard'));

    await expect(handler.handle({ count: 0 })).resolves.toBeNull();
  });

  it('should return null when the user is already on the history events page', async () => {
    const handler = createUnmatchedBridgeTransactionsHandler(mockT, createRouter('/history/events/'));

    await expect(handler.handle({ count: 3 })).resolves.toBeNull();
  });

  it('should return a persistent warning notification with the bridge group', async () => {
    const handler = createUnmatchedBridgeTransactionsHandler(mockT, createRouter('/dashboard'));

    const result = await handler.handle({ count: 3 });

    expect(result).toMatchObject({
      category: NotificationCategory.DEFAULT,
      display: true,
      group: NotificationGroup.UNMATCHED_BRIDGE_TRANSACTIONS,
      priority: Priority.ACTION,
      severity: Severity.WARNING,
    });

    const action = result?.action;
    assert(action && !Array.isArray(action));
    expect(action.persist).toBe(true);
  });

  it('should route to the history events page with the bridge dialog query on action', async () => {
    const router = createRouter('/dashboard');
    const handler = createUnmatchedBridgeTransactionsHandler(mockT, router);

    const result = await handler.handle({ count: 2 });
    const action = result?.action;
    assert(action && !Array.isArray(action));

    await action.action();

    expect(router.push).toHaveBeenCalledWith({
      name: '/history/events/',
      query: { openMatchBridgesDialog: 'true' },
    });
  });
});
