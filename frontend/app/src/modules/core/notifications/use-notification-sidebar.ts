import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { type NotificationData, Priority, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useSilentNotifications } from '@/modules/core/notifications/use-silent-notifications';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

export const TabCategory = {
  ERROR: 'error',
  NEEDS_ACTION: 'needs_action',
  REMINDER: 'reminder',
  VIEW_ALL: 'view_all',
} as const;

export type TabCategory = (typeof TabCategory)[keyof typeof TabCategory];

/** Order the tabs appear in, which is not the declaration order of {@link TabCategory}. */
export const TAB_ORDER: TabCategory[] = [
  TabCategory.VIEW_ALL,
  TabCategory.NEEDS_ACTION,
  TabCategory.REMINDER,
  TabCategory.ERROR,
];

const TAB_FILTERS: Partial<Record<TabCategory, (item: NotificationData) => boolean>> = {
  [TabCategory.ERROR]: (item: NotificationData) => item.severity === Severity.ERROR,
  [TabCategory.NEEDS_ACTION]: (item: NotificationData) => item.priority === Priority.ACTION,
  [TabCategory.REMINDER]: (item: NotificationData) => item.severity === Severity.REMINDER,
};

/** How long the pending-task list stays expanded after the last task finishes. */
const COLLAPSE_DEBOUNCE = 1000;

interface UseNotificationSidebarOptions {
  /** Two-way binding for the drawer; closing the sidebar writes `false` to it. */
  display: Ref<boolean>;
  /** Vertical scroll offset of the notification list. */
  scrollY: MaybeRefOrGetter<number>;
}

interface UseNotificationSidebarReturn {
  /** Every notification, in priority order, whatever tab is selected. */
  allNotifications: Readonly<Ref<NotificationData[]>>;
  /** Closes the drawer. */
  close: () => void;
  /** Whether any task is currently running. */
  hasRunningTasks: ComputedRef<boolean>;
  /**
   * Whether newly rendered rows should appear without waiting to be scrolled into view.
   *
   * @remarks
   * It resets on a tab change and on the list going from empty to populated, so a fresh list is
   * shown at once rather than a column of placeholders; while scrolling it tracks the top of the
   * list instead.
   */
  initialAppear: Readonly<Ref<boolean>>;
  /** Whether notifications were dropped because the store was full. */
  messageOverflow: Readonly<Ref<boolean>>;
  /** Whether the pending-task list is expanded. */
  modelPendingTasksExpanded: Ref<boolean>;
  /** The selected tab. */
  modelSelectedTab: Ref<TabCategory>;
  /** Dismisses a single notification. */
  remove: (id: number) => void;
  /** The notifications the selected tab admits. */
  selectedNotifications: ComputedRef<NotificationData[]>;
  /**
   * Asks for confirmation before discarding every notification.
   *
   * @remarks
   * Clearing is not undoable, so nothing is discarded until the dialog is confirmed.
   */
  showConfirmation: () => void;
  /** Whether popups are suppressed. */
  silent: Readonly<Ref<boolean>>;
  /** The tab labels, keyed by tab. */
  tabCategoriesLabel: ComputedRef<Record<TabCategory, string>>;
  /** Turns popup suppression on or off. */
  toggleSilentMode: () => void;
}

/**
 * Drives the notification drawer: the tab filtering, the silent-mode toggle, the clear-all
 * confirmation, and the appearance of rows as the list scrolls.
 *
 * @returns the list state the drawer renders and the actions its controls call
 */
export function useNotificationSidebar(options: UseNotificationSidebarOptions): UseNotificationSidebarReturn {
  const { display, scrollY } = options;

  const { t } = useI18n({ useScope: 'global' });

  const modelSelectedTab = shallowRef<TabCategory>(TabCategory.VIEW_ALL);
  const modelPendingTasksExpanded = shallowRef<boolean>(false);
  const initialAppear = shallowRef<boolean>(false);

  const notificationStore = useNotificationsStore();
  const { messageOverflow, prioritized: allNotifications } = storeToRefs(notificationStore);
  const { remove } = notificationStore;
  const { show } = useConfirmStore();
  const { isActive: hasRunningTasks } = useTaskCenter();
  const { silent, toggle: toggleSilent } = useSilentNotifications();

  const tabCategoriesLabel = computed<Record<TabCategory, string>>(() => ({
    [TabCategory.ERROR]: t('notification_sidebar.tabs.error'),
    [TabCategory.NEEDS_ACTION]: t('notification_sidebar.tabs.needs_action'),
    [TabCategory.REMINDER]: t('notification_sidebar.tabs.reminder'),
    [TabCategory.VIEW_ALL]: t('notification_sidebar.tabs.view_all'),
  }));

  const selectedNotifications = computed<NotificationData[]>(() => {
    const all = get(allNotifications);
    const filterBy = TAB_FILTERS[get(modelSelectedTab)];

    if (filterBy)
      return all.filter(filterBy);

    return all;
  });

  function close(): void {
    set(display, false);
  }

  function toggleSilentMode(): void {
    startPromise(toggleSilent());
  }

  function clear(): void {
    notificationStore.$reset();
    close();
  }

  function showConfirmation(): void {
    show({
      message: t('notification_sidebar.confirmation.message'),
      title: t('notification_sidebar.confirmation.title'),
      type: 'info',
    }, clear);
  }

  function collapsePendingTasksWhenIdle(running: boolean): void {
    if (!running)
      set(modelPendingTasksExpanded, false);
  }

  watchDebounced(hasRunningTasks, collapsePendingTasksWhenIdle, { debounce: COLLAPSE_DEBOUNCE });

  function trackRowAppearance(
    [currentY, currentTab, currentNotifications]: [number, TabCategory, NotificationData[]],
    [, previousTab, previousNotifications]: [number, TabCategory, NotificationData[]],
  ): void {
    const listArrived = previousNotifications.length === 0 && currentNotifications.length > 0;

    if (currentTab !== previousTab || listArrived) {
      set(initialAppear, false);
      startPromise(nextTick((): void => {
        set(initialAppear, true);
      }));
    }
    else {
      set(initialAppear, currentY <= 0);
    }
  }

  watch([(): number => toValue(scrollY), modelSelectedTab, selectedNotifications], trackRowAppearance);

  return {
    allNotifications,
    close,
    hasRunningTasks,
    initialAppear: readonly(initialAppear),
    messageOverflow,
    modelPendingTasksExpanded,
    modelSelectedTab,
    remove,
    selectedNotifications,
    showConfirmation,
    silent,
    tabCategoriesLabel,
    toggleSilentMode,
  };
}
