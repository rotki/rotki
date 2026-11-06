import type { ComputedRef, Ref } from 'vue';
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type { HistoryEventsActionFailure } from '@/modules/history/events/use-history-events-action-failure';
import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';
import { type DuplicateRow, type DuplicatesActionHandlers, useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';

/** The tabs, in the order the dialog renders them. */
export const DuplicatesTab = {
  AUTO_FIX: 0,
  IGNORED: 2,
  MANUAL_REVIEW: 1,
} as const;

interface DuplicateGroup {
  /** The group ids the domain composable found for this tab. */
  groupIds: ComputedRef<string[]>;
  loading: Ref<boolean>;
  /** Why the last read of this tab's rows failed; the rows of an earlier read stay. */
  error: Ref<unknown>;
  /** Why the last action started from this tab failed; cleared when the next action starts. */
  actionFailure: Ref<HistoryEventsActionFailure | undefined>;
  rows: Ref<DuplicateRow[]>;
  /** Bound with `v-model:selected` by the list, so it stays writable. */
  selected: Ref<string[]>;
}

interface UseCustomizedEventDuplicatesDialogOptions {
  /** Closes the dialog, which navigating away from it has to do first. */
  close: () => void;
}

interface UseCustomizedEventDuplicatesDialogReturn {
  /** All bound with `v-model`, so they stay writable. */
  modelActiveTab: Ref<number>;
  modelSelectedAutoFix: Ref<string[]>;
  modelSelectedManualReview: Ref<string[]>;
  modelSelectedIgnored: Ref<string[]>;
  /**
   * Shallow: the rows go straight into a prop typed `DuplicateRow[]`, which a deep `readonly()`
   * would turn into a `DeepReadonly` the prop cannot accept.
   */
  autoFixRows: Readonly<Ref<DuplicateRow[]>>;
  manualReviewRows: Readonly<Ref<DuplicateRow[]>>;
  ignoredRows: Readonly<Ref<DuplicateRow[]>>;
  autoFixLoading: Readonly<Ref<boolean>>;
  manualReviewLoading: Readonly<Ref<boolean>>;
  ignoredLoading: Readonly<Ref<boolean>>;
  /**
   * Why a tab could not be read: its own rows, or the group ids every tab is read from.
   *
   * @remarks
   * Kept for the tab to show in place of its rows, or above the rows an earlier read left, instead
   * of a toast per tab. Retry with {@link UseCustomizedEventDuplicatesDialogReturn.retry}.
   */
  autoFixError: ComputedRef<unknown>;
  manualReviewError: ComputedRef<unknown>;
  ignoredError: ComputedRef<unknown>;
  /** Why the last fix, dismissal or restore started from the tab failed, for the tab to name. */
  autoFixActionFailure: Readonly<Ref<HistoryEventsActionFailure | undefined>>;
  manualReviewActionFailure: Readonly<Ref<HistoryEventsActionFailure | undefined>>;
  ignoredActionFailure: Readonly<Ref<HistoryEventsActionFailure | undefined>>;
  /** Reads the duplicate group ids, then the events behind them. */
  initialize: () => Promise<void>;
  /** Reads one tab again; a failed read of the group ids reads everything again, since every tab needs them. */
  retry: (tab: number) => Promise<void>;
  /** These run once their button asked beside it, so they ask nothing themselves. */
  fixSingle: (groupId: string) => Promise<void>;
  fixSelected: () => Promise<void>;
  ignoreSingle: (groupId: string) => Promise<void>;
  ignoreSelected: () => Promise<void>;
  restoreSingle: (groupId: string) => Promise<void>;
  restoreSelected: () => Promise<void>;
  showInHistoryEvents: (groupIds: string[], status: DuplicateHandlingStatus) => Promise<void>;
}

/**
 * The duplicates dialog: three tabs over the same set of duplicate groups, each with its own rows,
 * its own selection and its own loading state.
 *
 * Every action is asked about beside the button that starts it. Its success callback touches
 * the dialog (the acted-on ids leave the selection and the affected tabs are re-read), and a failure
 * stays on the tab the action was started from. Fixing
 * only moves rows within the auto-fix tab, while ignoring and restoring move rows *between* tabs, so
 * those re-read all three.
 */
export function useCustomizedEventDuplicatesDialog(
  options: UseCustomizedEventDuplicatesDialogOptions,
): UseCustomizedEventDuplicatesDialogReturn {
  const { close } = options;

  const router = useRouter();

  const {
    autoFixGroupIds,
    fetchCustomizedEventDuplicates,
    fetchDuplicateEvents,
    fetchError,
    fixAndSettle,
    ignoredGroupIds,
    manualReviewGroupIds,
    markNonDuplicatedAndSettle,
    restoreAndSettle,
  } = useCustomizedEventDuplicates();

  const modelActiveTab = shallowRef<number>(DuplicatesTab.AUTO_FIX);

  const autoFix: DuplicateGroup = {
    actionFailure: shallowRef<HistoryEventsActionFailure>(),
    groupIds: autoFixGroupIds,
    error: shallowRef<unknown>(),
    loading: shallowRef<boolean>(false),
    rows: ref<DuplicateRow[]>([]),
    selected: ref<string[]>([]),
  };

  const manualReview: DuplicateGroup = {
    actionFailure: shallowRef<HistoryEventsActionFailure>(),
    groupIds: manualReviewGroupIds,
    error: shallowRef<unknown>(),
    loading: shallowRef<boolean>(false),
    rows: ref<DuplicateRow[]>([]),
    selected: ref<string[]>([]),
  };

  const ignored: DuplicateGroup = {
    actionFailure: shallowRef<HistoryEventsActionFailure>(),
    groupIds: ignoredGroupIds,
    error: shallowRef<unknown>(),
    loading: shallowRef<boolean>(false),
    rows: ref<DuplicateRow[]>([]),
    selected: ref<string[]>([]),
  };

  async function loadGroup(group: DuplicateGroup): Promise<void> {
    set(group.loading, true);
    set(group.error, undefined);
    try {
      const ids = get(group.groupIds);
      const result = await fetchDuplicateEvents({
        groupIds: ids,
        limit: ids.length || 1,
        offset: 0,
      });
      set(group.rows, result.data);
    }
    catch (error: unknown) {
      logger.error('Failed to load duplicate event rows:', error);
      set(group.error, error);
    }
    finally {
      set(group.loading, false);
    }
  }

  function failureOf(group: DuplicateGroup): ComputedRef<unknown> {
    return computed<unknown>(() => get(group.error) ?? get(fetchError));
  }

  async function loadAllGroups(): Promise<void> {
    await Promise.all([loadGroup(autoFix), loadGroup(manualReview), loadGroup(ignored)]);
  }

  /**
   * The handlers for an action started from `group`'s tab: its failure stays on that tab.
   *
   * @remarks
   * Starting an action clears the tab's last failure, so it never outlives the next attempt. `onSuccess` is what
   * the tab does once the action went through.
   */
  function handlersFor(group: DuplicateGroup, onSuccess: () => void): DuplicatesActionHandlers {
    set(group.actionFailure, undefined);
    return {
      onFailure: failure => set(group.actionFailure, failure),
      onSuccess,
    };
  }

  function deselect(group: DuplicateGroup, groupId: string): void {
    set(group.selected, get(group.selected).filter(id => id !== groupId));
  }

  async function initialize(): Promise<void> {
    await fetchCustomizedEventDuplicates();
    await loadAllGroups();
  }

  const groupsByTab = new Map<number, DuplicateGroup>([
    [DuplicatesTab.AUTO_FIX, autoFix],
    [DuplicatesTab.MANUAL_REVIEW, manualReview],
    [DuplicatesTab.IGNORED, ignored],
  ]);

  async function retry(tab: number): Promise<void> {
    const group = groupsByTab.get(tab);
    if (get(fetchError) !== undefined || !group)
      await initialize();
    else
      await loadGroup(group);
  }

  async function fixSingle(groupId: string): Promise<void> {
    await fixAndSettle([groupId], handlersFor(autoFix, () => {
      deselect(autoFix, groupId);
      startPromise(loadGroup(autoFix));
    }));
  }

  async function fixSelected(): Promise<void> {
    const selected = get(autoFix.selected);
    if (selected.length === 0)
      return;

    await fixAndSettle(selected, handlersFor(autoFix, () => {
      set(autoFix.selected, []);
      startPromise(loadGroup(autoFix));
    }));
  }

  async function ignoreSingle(groupId: string): Promise<void> {
    const group = get(modelActiveTab) === DuplicatesTab.MANUAL_REVIEW ? manualReview : autoFix;
    await markNonDuplicatedAndSettle([groupId], handlersFor(group, () => {
      deselect(autoFix, groupId);
      deselect(manualReview, groupId);
      startPromise(loadAllGroups());
    }));
  }

  async function ignoreSelected(): Promise<void> {
    const group = get(modelActiveTab) === DuplicatesTab.AUTO_FIX ? autoFix : manualReview;
    const selected = get(group.selected);
    if (selected.length === 0)
      return;

    await markNonDuplicatedAndSettle(selected, handlersFor(group, () => {
      set(group.selected, []);
      startPromise(loadAllGroups());
    }));
  }

  async function restoreSingle(groupId: string): Promise<void> {
    await restoreAndSettle([groupId], handlersFor(ignored, () => {
      deselect(ignored, groupId);
      startPromise(loadAllGroups());
    }));
  }

  async function restoreSelected(): Promise<void> {
    const selected = get(ignored.selected);
    if (selected.length === 0)
      return;

    await restoreAndSettle(selected, handlersFor(ignored, () => {
      set(ignored.selected, []);
      startPromise(loadAllGroups());
    }));
  }

  async function showInHistoryEvents(groupIds: string[], status: DuplicateHandlingStatus): Promise<void> {
    if (groupIds.length === 0)
      return;

    close();
    await router.push({
      name: '/history/events/',
      query: {
        duplicateHandlingStatus: status,
        groupIdentifiers: groupIds.join(','),
      },
    });
  }

  return {
    autoFixActionFailure: shallowReadonly(autoFix.actionFailure),
    autoFixError: failureOf(autoFix),
    autoFixLoading: readonly(autoFix.loading),
    autoFixRows: shallowReadonly(autoFix.rows),
    fixSelected,
    fixSingle,
    ignoreSelected,
    ignoreSingle,
    ignoredActionFailure: shallowReadonly(ignored.actionFailure),
    ignoredError: failureOf(ignored),
    ignoredLoading: readonly(ignored.loading),
    ignoredRows: shallowReadonly(ignored.rows),
    initialize,
    manualReviewActionFailure: shallowReadonly(manualReview.actionFailure),
    manualReviewError: failureOf(manualReview),
    manualReviewLoading: readonly(manualReview.loading),
    manualReviewRows: shallowReadonly(manualReview.rows),
    modelActiveTab,
    modelSelectedAutoFix: autoFix.selected,
    modelSelectedIgnored: ignored.selected,
    modelSelectedManualReview: manualReview.selected,
    restoreSelected,
    restoreSingle,
    retry,
    showInHistoryEvents,
  };
}
