import { type NotificationData, NotificationGroup, NotificationKind, Severity } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia, storeToRefs } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { groupMuteKey, problemMuteKey } from '@/modules/core/notifications/use-notification-mute';
import { useNotificationUnread } from '@/modules/core/notifications/use-notification-unread';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';

const { muted } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { muted: ref<string[]>([]) };
});

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => muted),
}));

vi.mock('@/modules/settings/use-frontend-settings-writer', () => ({
  useFrontendSettingsWriter: vi.fn(() => ({ updateFrontendSetting: vi.fn() })),
}));

function tokens(read: boolean): NotificationData {
  return {
    date: new Date('2026-03-04T05:06:07Z'),
    display: false,
    duration: 5000,
    group: NotificationGroup.NEW_DETECTED_TOKENS,
    id: 1,
    kind: NotificationKind.ANNOUNCEMENT,
    message: 'new tokens',
    read,
    severity: Severity.INFO,
    title: 'new tokens',
  };
}

function fileNetworkProblem(): void {
  useBackendProblemsStore().record({
    at: new Date('2026-03-04T05:06:07Z'),
    count: 1,
    identity: 'kraken',
    source: { fields: { error: 'timeout', record: 'balance' }, group: ['error', 'network', 'kraken'], key: 'network', subject: 'kraken', value: 'kraken timed out', verbosity: 'error' },
  });
}

describe('modules/core/notifications/useNotificationUnread', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    muted.value = [];
  });

  it('should light for an unread notification', () => {
    set(storeToRefs(useNotificationsStore()).data, [tokens(false)]);

    expect(get(useNotificationUnread().hasUnread)).toBe(true);
  });

  it('should stay dark once everything is read', () => {
    set(storeToRefs(useNotificationsStore()).data, [tokens(true)]);

    expect(get(useNotificationUnread().hasUnread)).toBe(false);
  });

  it('should stay dark for an unread notification of a muted group', () => {
    muted.value = [groupMuteKey(NotificationGroup.NEW_DETECTED_TOKENS)];
    set(storeToRefs(useNotificationsStore()).data, [tokens(false)]);

    expect(get(useNotificationUnread().hasUnread)).toBe(false);
  });

  it('should light for an unread backend problem', () => {
    fileNetworkProblem();

    expect(get(useNotificationUnread().hasUnread)).toBe(true);
  });

  it('should stay dark for an unread backend problem whose family and location are muted', () => {
    muted.value = [problemMuteKey({ key: 'network', subject: 'kraken' })];
    fileNetworkProblem();

    expect(get(useNotificationUnread().hasUnread)).toBe(false);
  });
});
