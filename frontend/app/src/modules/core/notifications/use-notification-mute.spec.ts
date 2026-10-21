import { NotificationGroup, NotificationKind } from '@rotki/common';
import { describe, expect, it, vi } from 'vitest';
import { BALANCE_SNAPSHOT } from '@/modules/core/notifications/problems/backend-problem-tree';
import {
  groupMuteKey,
  notificationMuteKey,
  problemMuteKey,
  useNotificationMute,
} from '@/modules/core/notifications/use-notification-mute';

const { muted, updateFrontendSetting } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    muted: ref<string[]>([]),
    updateFrontendSetting: vi.fn<(payload: { mutedNotificationGroups: string[] }) => Promise<{ success: boolean }>>(),
  };
});

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => muted),
}));

vi.mock('@/modules/settings/use-frontend-settings-writer', () => ({
  useFrontendSettingsWriter: vi.fn(() => ({ updateFrontendSetting })),
}));

/** A write that lands only once released, updating the setting then, as the real writer does. */
function holdWrites(): { release: () => void } {
  const waiting: (() => void)[] = [];
  updateFrontendSetting.mockImplementation(async ({ mutedNotificationGroups }) => new Promise((resolve) => {
    waiting.push(() => {
      muted.value = mutedNotificationGroups;
      resolve({ success: true });
    });
  }));
  return { release: () => waiting.shift()?.() };
}

describe('modules/core/notifications/useNotificationMute', () => {
  it('should keep both mutes when the second is asked for before the first is saved', async () => {
    muted.value = [];
    const { release } = holdWrites();
    const { mute } = useNotificationMute();

    const first = mute('problem:network:kraken');
    const second = mute('group:new_detected_tokens');
    await Promise.resolve();
    release();
    await first;
    release();
    await second;

    expect(muted.value).toEqual(['problem:network:kraken', 'group:new_detected_tokens']);
  });

  it('should not undo a mute still in flight when a different key is unmuted', async () => {
    muted.value = ['group:new_detected_tokens'];
    const { release } = holdWrites();
    const { mute, unmute } = useNotificationMute();

    const muting = mute('problem:network:kraken');
    const unmuting = unmute('group:new_detected_tokens');
    await Promise.resolve();
    release();
    await muting;
    release();
    await unmuting;

    expect(muted.value).toEqual(['problem:network:kraken']);
  });
});

describe('modules/core/notifications/use-notification-mute', () => {
  it('should key a backend problem by family and location, so one mute covers every severity of it', () => {
    expect(problemMuteKey({ key: 'network', subject: 'kraken' })).toBe('problem:network:kraken');
    expect(problemMuteKey({ key: BALANCE_SNAPSHOT, subject: 'kraken' })).toBe('problem:balance_snapshot:kraken');
  });

  it('should key a backend problem with no location by its family alone', () => {
    expect(problemMuteKey({ key: 'local_db', subject: null })).toBe('problem:local_db:');
  });

  it('should offer to mute a grouped announcement by its group', () => {
    const key = notificationMuteKey({ group: NotificationGroup.NEW_DETECTED_TOKENS, kind: NotificationKind.ANNOUNCEMENT });

    expect(key).toBe(groupMuteKey(NotificationGroup.NEW_DETECTED_TOKENS));
  });

  it.each([
    ['an ungrouped announcement', { kind: NotificationKind.ANNOUNCEMENT }],
    ['a grouped result', { group: NotificationGroup.MONERIUM_AUTH, kind: NotificationKind.RESULT }],
    ['a reminder', { kind: NotificationKind.REMINDER }],
    ['a failure', { group: NotificationGroup.ASSET_MAPPINGS, kind: NotificationKind.FAILURE }],
  ])('should not offer to mute %s', (_case, notification) => {
    expect(notificationMuteKey(notification)).toBeUndefined();
  });
});
