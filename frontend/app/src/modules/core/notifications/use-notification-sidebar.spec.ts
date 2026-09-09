import { NotificationCategory, type NotificationData, Priority, Severity } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises } from '@vue/test-utils';
import { setActivePinia, storeToRefs } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, effectScope, nextTick, type Ref, ref } from 'vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { TAB_ORDER, TabCategory, useNotificationSidebar } from './use-notification-sidebar';

interface MockedDependencies {
  isActive?: Ref<boolean>;
  silent?: Ref<boolean>;
}

const { deps, toggleSilent } = vi.hoisted(() => {
  const deps: MockedDependencies = {};
  return { deps, toggleSilent: vi.fn(async () => Promise.resolve()) };
});

let isActive: Ref<boolean>;
let silent: Ref<boolean>;

vi.mock('@/modules/core/notifications/use-notification-cooldown', () => ({
  useNotificationCooldown: vi.fn(() => ({
    recordDisplay: vi.fn(),
    resetSchedule: vi.fn(),
    shouldSuppress: vi.fn(() => false),
  })),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ isActive: deps.isActive }),
}));

vi.mock('@/modules/core/notifications/use-silent-notifications', () => ({
  useSilentNotifications: (): Record<string, unknown> => ({
    silent: deps.silent,
    toggle: toggleSilent,
  }),
}));

function notification(overrides: Partial<NotificationData> = {}): NotificationData {
  return {
    category: NotificationCategory.DEFAULT,
    date: new Date('2026-03-04T05:06:07Z'),
    display: true,
    duration: 5000,
    id: 1,
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
    isActive = ref<boolean>(false);
    silent = ref<boolean>(false);
    deps.isActive = isActive;
    deps.silent = silent;
    set(display, true);
    set(scrollY, 0);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the tabs', () => {
    it('should show the tabs in the order the drawer lays them out', () => {
      expect(TAB_ORDER).toEqual([
        TabCategory.VIEW_ALL,
        TabCategory.NEEDS_ACTION,
        TabCategory.REMINDER,
        TabCategory.ERROR,
      ]);
    });

    it('should label every tab it offers', () => {
      const { tabCategoriesLabel } = sidebar();

      for (const tab of TAB_ORDER)
        expect(get(tabCategoriesLabel)[tab]).toBe(`notification_sidebar.tabs.${tab}`);
    });
  });

  describe('filtering by tab', () => {
    const error = notification({ id: 1, severity: Severity.ERROR });
    const reminder = notification({ id: 2, severity: Severity.REMINDER });
    const needsAction = notification({ id: 3, priority: Priority.ACTION, severity: Severity.INFO });

    beforeEach(() => {
      seed([error, reminder, needsAction]);
    });

    it('should hold everything back on the view-all tab', () => {
      const { selectedNotifications } = sidebar();

      expect(get(selectedNotifications)).toHaveLength(3);
    });

    it.each([
      [TabCategory.ERROR, 1],
      [TabCategory.REMINDER, 2],
      [TabCategory.NEEDS_ACTION, 3],
    ])('should show only what the %s tab admits', (tab, expectedId) => {
      const { modelSelectedTab, selectedNotifications } = sidebar();
      set(modelSelectedTab, tab);

      expect(get(selectedNotifications).map(item => item.id)).toEqual([expectedId]);
    });
  });

  describe('clearing every notification', () => {
    beforeEach(() => {
      seed([notification({ id: 1 }), notification({ id: 2 })]);
    });

    it('should discard nothing until the dialog is confirmed', () => {
      const { allNotifications, showConfirmation } = sidebar();
      showConfirmation();

      expect(get(useConfirmStore().visible)).toBe(true);
      expect(get(allNotifications)).toHaveLength(2);
      expect(get(display)).toBe(true);
    });

    it('should discard them and close the drawer once confirmed', async () => {
      const { allNotifications, showConfirmation } = sidebar();
      showConfirmation();
      await useConfirmStore().confirm();

      expect(get(allNotifications)).toHaveLength(0);
      expect(get(display)).toBe(false);
    });

    it('should discard nothing when the dialog is dismissed', async () => {
      const { allNotifications, showConfirmation } = sidebar();
      showConfirmation();
      await useConfirmStore().dismiss();

      expect(get(allNotifications)).toHaveLength(2);
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

  describe('the pending task list', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should collapse it once the tasks have been idle long enough', async () => {
      set(isActive, true);
      const { modelPendingTasksExpanded } = sidebar();
      set(modelPendingTasksExpanded, true);

      set(isActive, false);
      await nextTick();
      await vi.advanceTimersByTimeAsync(1000);

      expect(get(modelPendingTasksExpanded)).toBe(false);
    });

    it('should leave it expanded while tasks are still running', async () => {
      const { modelPendingTasksExpanded } = sidebar();
      set(modelPendingTasksExpanded, true);

      set(isActive, true);
      await nextTick();
      await vi.advanceTimersByTimeAsync(1000);

      expect(get(modelPendingTasksExpanded)).toBe(true);
    });
  });

  describe('how rows appear', () => {
    it('should show a freshly filtered list at once rather than on scroll', async () => {
      seed([notification({ id: 1, severity: Severity.ERROR })]);
      const { initialAppear, modelSelectedTab } = sidebar();

      set(modelSelectedTab, TabCategory.ERROR);
      await flushPromises();

      expect(get(initialAppear)).toBe(true);
    });

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
