import type { ComputedRef, Ref } from 'vue';
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';
import { type DuplicateRow, useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';

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
   * of a toast per tab. Retry with {@link UseCustomizedEventDuplicatesDialogReturn.initialize}.
   */
  autoFixError: ComputedRef<unknown>;
  manualReviewError: ComputedRef<unknown>;
  ignoredError: ComputedRef<unknown>;
  /** Reads the duplicate group ids, then the events behind them. */
  initialize: () => Promise<void>;
  fixSingle: (groupId: string) => void;
  fixSelected: () => void;
  ignoreSingle: (groupId: string) => void;
  ignoreSelected: () => void;
  restoreSingle: (groupId: string) => void;
  restoreSelected: () => void;
  showInHistoryEvents: (groupIds: string[], status: DuplicateHandlingStatus) => Promise<void>;
}

/**
 * The duplicates dialog: three tabs over the same set of duplicate groups, each with its own rows,
 * its own selection and its own loading state.
 *
 * Every action goes through a confirmation the domain composable owns, and only its success callback
 * touches the dialog: the acted-on ids leave the selection and the affected tabs are re-read. Fixing
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
    confirmAndFixDuplicate,
    confirmAndMarkNonDuplicated,
    confirmAndRestore,
    fetchCustomizedEventDuplicates,
    fetchDuplicateEvents,
    fetchError,
    ignoredGroupIds,
    manualReviewGroupIds,
  } = useCustomizedEventDuplicates();

  const modelActiveTab = shallowRef<number>(DuplicatesTab.AUTO_FIX);

  const autoFix: DuplicateGroup = {
    groupIds: autoFixGroupIds,
    error: shallowRef<unknown>(),
    loading: shallowRef<boolean>(false),
    rows: ref<DuplicateRow[]>([]),
    selected: ref<string[]>([]),
  };

  const manualReview: DuplicateGroup = {
    groupIds: manualReviewGroupIds,
    error: shallowRef<unknown>(),
    loading: shallowRef<boolean>(false),
    rows: ref<DuplicateRow[]>([]),
    selected: ref<string[]>([]),
  };

  const ignored: DuplicateGroup = {
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

  function deselect(group: DuplicateGroup, groupId: string): void {
    set(group.selected, get(group.selected).filter(id => id !== groupId));
  }

  async function initialize(): Promise<void> {
    await fetchCustomizedEventDuplicates();
    await loadAllGroups();
  }

  function fixSingle(groupId: string): void {
    confirmAndFixDuplicate([groupId], () => {
      deselect(autoFix, groupId);
      startPromise(loadGroup(autoFix));
    });
  }

  function fixSelected(): void {
    const selected = get(autoFix.selected);
    if (selected.length === 0)
      return;

    confirmAndFixDuplicate(selected, () => {
      set(autoFix.selected, []);
      startPromise(loadGroup(autoFix));
    });
  }

  function ignoreSingle(groupId: string): void {
    confirmAndMarkNonDuplicated([groupId], () => {
      deselect(autoFix, groupId);
      deselect(manualReview, groupId);
      startPromise(loadAllGroups());
    });
  }

  function ignoreSelected(): void {
    const group = get(modelActiveTab) === DuplicatesTab.AUTO_FIX ? autoFix : manualReview;
    const selected = get(group.selected);
    if (selected.length === 0)
      return;

    confirmAndMarkNonDuplicated(selected, () => {
      set(group.selected, []);
      startPromise(loadAllGroups());
    });
  }

  function restoreSingle(groupId: string): void {
    confirmAndRestore([groupId], () => {
      deselect(ignored, groupId);
      startPromise(loadAllGroups());
    });
  }

  function restoreSelected(): void {
    const selected = get(ignored.selected);
    if (selected.length === 0)
      return;

    confirmAndRestore(selected, () => {
      set(ignored.selected, []);
      startPromise(loadAllGroups());
    });
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
    autoFixError: failureOf(autoFix),
    autoFixLoading: readonly(autoFix.loading),
    autoFixRows: shallowReadonly(autoFix.rows),
    fixSelected,
    fixSingle,
    ignoreSelected,
    ignoreSingle,
    ignoredError: failureOf(ignored),
    ignoredLoading: readonly(ignored.loading),
    ignoredRows: shallowReadonly(ignored.rows),
    initialize,
    manualReviewError: failureOf(manualReview),
    manualReviewLoading: readonly(manualReview.loading),
    manualReviewRows: shallowReadonly(manualReview.rows),
    modelActiveTab,
    modelSelectedAutoFix: autoFix.selected,
    modelSelectedIgnored: ignored.selected,
    modelSelectedManualReview: manualReview.selected,
    restoreSelected,
    restoreSingle,
    showInHistoryEvents,
  };
}
