import { type NotificationData, NotificationGroup, NotificationKind, Severity } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises } from '@vue/test-utils';
import { setActivePinia, storeToRefs } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, effectScope, nextTick, type Ref, ref } from 'vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useNotificationSidebar } from './use-notification-sidebar';

interface MockedDependencies {
  silent?: Ref<boolean>;
}

const { deps, toggleSilent, updateFrontendSetting } = vi.hoisted(() => {
  const deps: MockedDependencies = {};
  return {
    deps,
    toggleSilent: vi.fn(async () => Promise.resolve()),
    updateFrontendSetting: vi.fn<(update: Record<string, unknown>) => Promise<void>>(async () => Promise.resolve()),
  };
});

vi.mock('@/modules/settings/use-frontend-settings-writer', () => ({
  useFrontendSettingsWriter: (): Record<string, unknown> => ({ updateFrontendSetting }),
}));

let silent: Ref<boolean>;

vi.mock('@/modules/core/notifications/use-notification-cooldown', () => ({
  useNotificationCooldown: vi.fn(() => ({
    recordDisplay: vi.fn(),
    shouldSuppress: vi.fn(() => false),
  })),
}));

vi.mock('@/modules/core/notifications/use-silent-notifications', () => ({
  useSilentNotifications: (): Record<string, unknown> => ({
    silent: deps.silent,
    toggle: toggleSilent,
  }),
}));

function notification(overrides: Partial<NotificationData> = {}): NotificationData {
  return {
    date: new Date('2026-03-04T05:06:07Z'),
    display: true,
    duration: 5000,
    id: 1,
    kind: NotificationKind.RESULT,
    message: 'the message',
    read: false,
    severity: Severity.INFO,
    title: 'the title',
    ...overrides,
  };
}

const display = ref<boolean>(true);
const scrollY = ref<number>(0);
let scope: ReturnType<typeof effectScope>;

function sidebar(): ReturnType<typeof useNotificationSidebar> {
  scope = effectScope();
  return scope.run(() => useNotificationSidebar({ display, scrollY }))!;
}

function seed(notifications: NotificationData[]): void {
  set(storeToRefs(useNotificationsStore()).data, notifications);
}

function fileProblem(): void {
  useBackendProblemsStore().record({
    at: new Date('2026-03-04T05:06:07Z'),
    count: 1,
    identity: 'tag',
    source: { fields: { entry: 'tag' }, group: ['error', 'local_db', null, 'tag'], key: 'local_db', subject: null, value: 'Could not read a tag', verbosity: 'error' },
  });
}

/**
 * `pinia.use()` only queues a plugin; `install(app)` is what moves it into the active list. A spec
 * that calls `setActivePinia` and never mounts anything therefore runs with no plugins at all, and
 * `$reset` stays pinia's setup-store version, which throws. Installing into a bare app gives the
 * store the same `$reset` the application wires up in `main.ts`.
 */
function activatePinia(): void {
  const pinia = createCustomPinia();
  createApp({}).use(pinia);
  setActivePinia(pinia);
}

describe('modules/core/notifications/useNotificationSidebar', () => {
  beforeEach(() => {
    activatePinia();
    vi.clearAllMocks();
    silent = ref<boolean>(false);
    deps.silent = silent;
    set(display, true);
    set(scrollY, 0);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the day headers', () => {
    afterEach(() => {
      vi.useRealTimers();
    });

    it('should move a notification from today to yesterday at midnight while the drawer stays mounted', async () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(2026, 2, 4, 23, 59));
      seed([notification({ date: new Date(2026, 2, 4, 23, 0) })]);
      const { historyDays } = sidebar();
      expect(get(historyDays)[0].label).toBe('today');

      vi.advanceTimersByTime(2 * 60_000);
      await nextTick();

      expect(get(historyDays)[0].label).toBe('yesterday');
    });
  });

  describe('the history and the problems section', () => {
    const result = notification({ id: 1, kind: NotificationKind.RESULT });
    const reminder = notification({ id: 2, kind: NotificationKind.REMINDER });
    const failure = notification({ id: 3, kind: NotificationKind.FAILURE, severity: Severity.ERROR });

    beforeEach(() => {
      seed([result, reminder, failure]);
    });

    it('should keep the failures out of the history', () => {
      const { historyDays } = sidebar();

      expect(get(historyDays).flatMap(day => day.notifications.map(item => item.id)).sort()).toEqual([1, 2]);
    });

    it('should file the failures in the problems section', () => {
      const { failures } = sidebar();

      expect(get(failures).map(item => item.id)).toEqual([3]);
    });

    it('should open the problems section by default', () => {
      const { modelProblemsOpen } = sidebar();

      expect(get(modelProblemsOpen)).toBe(true);
    });
  });

  describe('muted groups', () => {
    it('should move a muted problem and a muted announcement group into the muted section', () => {
      useSettingsRepo().updateFrontend({ mutedNotificationGroups: ['problem:local_db:', 'group:NEW_DETECTED_TOKENS'] });
      fileProblem();
      seed([
        notification({ group: NotificationGroup.NEW_DETECTED_TOKENS, id: 1, kind: NotificationKind.ANNOUNCEMENT }),
        notification({ id: 2, kind: NotificationKind.ANNOUNCEMENT }),
      ]);

      const { historyDays, modelMutedOpen, muted, problems } = sidebar();

      expect(get(problems)).toEqual([]);
      expect(get(historyDays).flatMap(day => day.notifications.map(item => item.id))).toEqual([2]);
      expect(get(muted).problems).toHaveLength(1);
      expect(get(muted).notifications.map(item => item.id)).toEqual([1]);
      expect(get(modelMutedOpen)).toBe(false);
    });

    it('should write the mute key of the problem it mutes', async () => {
      fileProblem();
      const { muteProblem, problems } = sidebar();

      muteProblem(get(problems)[0]);
      await flushPromises();

      expect(updateFrontendSetting).toHaveBeenCalledWith({ mutedNotificationGroups: ['problem:local_db:'] });
    });
  });

  describe('backend problems', () => {
    beforeEach(() => {
      fileProblem();
    });

    it('should hand the drawer every problem', () => {
      const { problems } = sidebar();

      expect(get(problems)).toHaveLength(1);
    });

    it('should not count as empty while it holds only a problem', () => {
      const { isEmpty } = sidebar();

      expect(get(isEmpty)).toBe(false);
    });

    it('should mark the problems read once the drawer is open', async () => {
      sidebar();
      await nextTick();

      expect(get(storeToRefs(useBackendProblemsStore()).hasUnread)).toBe(false);
    });
  });

  describe('clearing every notification', () => {
    beforeEach(() => {
      seed([notification({ id: 1 }), notification({ id: 2 })]);
      fileProblem();
    });

    it('should discard nothing until the dialog is confirmed', () => {
      const { isEmpty, showConfirmation } = sidebar();
      showConfirmation();

      expect(get(useConfirmStore().visible)).toBe(true);
      expect(get(isEmpty)).toBe(false);
      expect(get(display)).toBe(true);
    });

    it('should discard the notifications and the problems, and close the drawer once confirmed', async () => {
      const { isEmpty, showConfirmation } = sidebar();
      showConfirmation();
      await useConfirmStore().confirm();

      expect(get(storeToRefs(useNotificationsStore()).data)).toHaveLength(0);
      expect(get(storeToRefs(useBackendProblemsStore()).problems)).toHaveLength(0);
      expect(get(isEmpty)).toBe(true);
      expect(get(display)).toBe(false);
    });

    it('should discard nothing when the dialog is dismissed', async () => {
      const { isEmpty, showConfirmation } = sidebar();
      showConfirmation();
      await useConfirmStore().dismiss();

      expect(get(storeToRefs(useNotificationsStore()).data)).toHaveLength(2);
      expect(get(isEmpty)).toBe(false);
      expect(get(display)).toBe(true);
    });
  });

  describe('consuming the new-notification dot', () => {
    it('should leave notifications unread while the drawer stays closed', async () => {
      set(display, false);
      seed([notification({ id: 1 })]);
      sidebar();
      await nextTick();

      expect(get(storeToRefs(useNotificationsStore()).data)[0].read).toBe(false);
    });

    it('should mark everything read once the drawer opens', async () => {
      set(display, false);
      seed([notification({ id: 1 }), notification({ id: 2 })]);
      sidebar();
      await nextTick();

      expect(get(storeToRefs(useNotificationsStore()).data).some(({ read }) => read)).toBe(false);

      set(display, true);
      await nextTick();

      expect(get(storeToRefs(useNotificationsStore()).data).every(({ read }) => read)).toBe(true);
    });

    it('should mark a notification arriving while the drawer is open', async () => {
      seed([notification({ id: 1 })]);
      sidebar();
      await nextTick();

      seed([notification({ id: 1, read: true }), notification({ id: 2 })]);
      await nextTick();

      expect(get(storeToRefs(useNotificationsStore()).data).every(({ read }) => read)).toBe(true);
    });
  });

  describe('the drawer controls', () => {
    it('should close the drawer', () => {
      const { close } = sidebar();
      close();

      expect(get(display)).toBe(false);
    });

    it('should toggle silent mode', () => {
      const { toggleSilentMode } = sidebar();
      toggleSilentMode();

      expect(toggleSilent).toHaveBeenCalledOnce();
    });

    it('should read silent mode from the setting', () => {
      set(silent, true);

      const { silent: isSilent } = sidebar();

      expect(get(isSilent)).toBe(true);
    });
  });

  describe('how rows appear', () => {
    it('should show the first notifications to arrive at once', async () => {
      const { initialAppear } = sidebar();

      seed([notification({ id: 1 })]);
      await flushPromises();

      expect(get(initialAppear)).toBe(true);
    });

    it('should follow the top of the list once it is scrolled', async () => {
      seed([notification({ id: 1 }), notification({ id: 2 })]);
      const { initialAppear } = sidebar();

      set(scrollY, 120);
      await flushPromises();

      expect(get(initialAppear)).toBe(false);

      set(scrollY, 0);
      await flushPromises();

      expect(get(initialAppear)).toBe(true);
    });
  });
});
