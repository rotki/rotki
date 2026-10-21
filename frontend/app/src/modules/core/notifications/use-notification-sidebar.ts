import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { BackendProblem } from '@/modules/core/notifications/problems/backend-problem-tree';
import { type NotificationData, NotificationKind } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { groupByDay, type NotificationDay, startOfDay } from '@/modules/core/notifications/notification-days';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useSilentNotifications } from '@/modules/core/notifications/use-silent-notifications';

/**
 * How often the drawer checks the clock, so "Today" and "Yesterday" move on at midnight while the
 * app stays open. The grouping itself reruns only when the day changes.
 */
const DAY_LABEL_TICK_MS = 60_000;

interface UseNotificationSidebarOptions {
  /** Two-way binding for the drawer; closing the sidebar writes `false` to it. */
  display: Ref<boolean>;
  /** Vertical scroll offset of the notification list. */
  scrollY: MaybeRefOrGetter<number>;
}

interface UseNotificationSidebarReturn {
  /** Results, announcements and reminders, by the day they arrived, newest day first. */
  historyDays: ComputedRef<NotificationDay[]>;
  /** Background requests that failed with nowhere else to show it, newest first. */
  failures: ComputedRef<NotificationData[]>;
  /** The backend problems tree, newest first. */
  problems: Readonly<Ref<BackendProblem[]>>;
  /** Whether the problems section is open. */
  modelProblemsOpen: Ref<boolean>;
  /** Whether the drawer holds neither a notification nor a backend problem. */
  isEmpty: ComputedRef<boolean>;
  /** Dismisses one backend problem with every item under it. */
  removeProblem: (id: string) => void;
  /** Closes the drawer. */
  close: () => void;
  /**
   * Whether newly rendered rows should appear without waiting to be scrolled into view.
   *
   * @remarks
   * It resets when the history goes from empty to populated, so a fresh list is shown at once
   * rather than a column of placeholders; while scrolling it tracks the top of the list instead.
   */
  initialAppear: Readonly<Ref<boolean>>;
  /** Whether notifications were dropped because the store was full. */
  messageOverflow: Readonly<Ref<boolean>>;
  /** Dismisses a single notification. */
  remove: (id: number) => void;
  /**
   * Asks for confirmation before discarding every notification.
   *
   * @remarks
   * Clearing is not undoable, so nothing is discarded until the dialog is confirmed.
   */
  showConfirmation: () => void;
  /** Whether popups are suppressed. */
  silent: Readonly<Ref<boolean>>;
  /** Turns popup suppression on or off. */
  toggleSilentMode: () => void;
}

/**
 * Drives the notification drawer: its history by day and its problems section, the silent-mode
 * toggle, the clear-all confirmation, and the appearance of rows as the list scrolls.
 *
 * @remarks
 * The history holds what happened (results, announcements, reminders). The problems section holds
 * what went wrong in the background: the backend problems tree, then the failures, which never pop
 * and so are only ever read here.
 *
 * @returns the list state the drawer renders and the actions its controls call
 */
export function useNotificationSidebar(options: UseNotificationSidebarOptions): UseNotificationSidebarReturn {
  const { display, scrollY } = options;

  const { t } = useI18n({ useScope: 'global' });

  const initialAppear = shallowRef<boolean>(false);
  const modelProblemsOpen = shallowRef<boolean>(true);

  const notificationStore = useNotificationsStore();
  const { messageOverflow, newestFirst: allNotifications } = storeToRefs(notificationStore);
  const { markAllRead, remove } = notificationStore;
  const problemsStore = useBackendProblemsStore();
  const { problems } = storeToRefs(problemsStore);
  const { markAllRead: markProblemsRead, remove: removeProblem } = problemsStore;
  const { show } = useConfirmStore();
  const { silent, toggle: toggleSilent } = useSilentNotifications();

  const history = computed<NotificationData[]>(() => get(allNotifications).filter(item => item.kind !== NotificationKind.FAILURE));

  const now = useNow({ scheduler: tick => useIntervalFn(tick, DAY_LABEL_TICK_MS) });
  const today = computed<number>(() => startOfDay(get(now)).getTime());

  const historyDays = computed<NotificationDay[]>(() => groupByDay(get(history), new Date(get(today))));

  const failures = computed<NotificationData[]>(() => get(allNotifications).filter(item => item.kind === NotificationKind.FAILURE));

  const isEmpty = computed<boolean>(() => get(allNotifications).length === 0 && get(problems).length === 0);

  function close(): void {
    set(display, false);
  }

  /**
   * Clears the "something new" dot as soon as the drawer is open.
   *
   * @remarks
   * Notifications arriving while it stays open are marked too, so the dot cannot light up behind
   * a drawer the user is already looking at. Items that need the user keep their place on the
   * badge; only the novelty signal is consumed here.
   */
  watchImmediate([display, allNotifications, problems], ([open]) => {
    if (!open)
      return;

    markAllRead();
    markProblemsRead();
  });

  function toggleSilentMode(): void {
    startPromise(toggleSilent());
  }

  function clear(): void {
    notificationStore.$reset();
    problemsStore.$reset();
    close();
  }

  function showConfirmation(): void {
    show({
      message: t('notification_sidebar.confirmation.message'),
      title: t('notification_sidebar.confirmation.title'),
      type: 'info',
    }, clear);
  }

  function trackRowAppearance(
    [currentY, current]: [number, NotificationData[]],
    [, previous]: [number, NotificationData[]],
  ): void {
    if (previous.length === 0 && current.length > 0) {
      set(initialAppear, false);
      startPromise(nextTick((): void => {
        set(initialAppear, true);
      }));
    }
    else {
      set(initialAppear, currentY <= 0);
    }
  }

  watch([(): number => toValue(scrollY), allNotifications], trackRowAppearance);

  return {
    close,
    failures,
    historyDays,
    initialAppear: readonly(initialAppear),
    isEmpty,
    messageOverflow,
    modelProblemsOpen,
    problems,
    remove,
    removeProblem,
    showConfirmation,
    silent,
    toggleSilentMode,
  };
}
