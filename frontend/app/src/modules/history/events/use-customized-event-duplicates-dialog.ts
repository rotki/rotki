import type { ComputedRef, Ref } from 'vue';
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { startPromise } from '@shared/utils';
import { tap } from 'plainfp/result';
import { logger } from '@/modules/core/common/logging/logging';
import { type DuplicateRow, useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';
import { type FailureSlot, type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';

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
  actionFailure: FailureSlot;
  rows: Ref<DuplicateRow[]>;
  /** Bound with `v-model:selected` by the list, so it stays writable. */
  selected: Ref<string[]>;
}

/** A tab over `groupIds`, with nothing read, selected or failed yet. */
function createGroup(groupIds: ComputedRef<string[]>): DuplicateGroup {
  return {
    actionFailure: useFailureSlot(),
    error: shallowRef<unknown>(),
    groupIds,
    loading: shallowRef<boolean>(false),
    rows: ref<DuplicateRow[]>([]),
    selected: ref<string[]>([]),
  };
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
  autoFixActionFailure: Readonly<Ref<NamedFailure | undefined>>;
  manualReviewActionFailure: Readonly<Ref<NamedFailure | undefined>>;
  ignoredActionFailure: Readonly<Ref<NamedFailure | undefined>>;
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
 * Every action is asked about beside the button that starts it. Its success touches the dialog
 * (the acted-on ids leave the selection and the affected tabs are re-read), and a failure stays on
 * the tab the action was started from. Fixing
 * only moves rows within the auto-fix tab, while ignoring and restoring move rows *between* tabs, so
 * those re-read all three.
 */
export function useCustomizedEventDuplicatesDialog(
  options: UseCustomizedEventDuplicatesDialogOptions,
): UseCustomizedEventDuplicatesDialogReturn {
  const { close } = options;

  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();

  const {
    autoFixGroupIds,
    fetchCustomizedEventDuplicates,
    fetchDuplicateEvents,
    fetchError,
    fixDuplicates,
    ignoreDuplicates,
    ignoredGroupIds,
    manualReviewGroupIds,
    unignoreDuplicates,
  } = useCustomizedEventDuplicates();

  const modelActiveTab = shallowRef<number>(DuplicatesTab.AUTO_FIX);

  const autoFix = createGroup(autoFixGroupIds);
  const manualReview = createGroup(manualReviewGroupIds);
  const ignored = createGroup(ignoredGroupIds);

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
    await autoFix.actionFailure.run(t('actions.customized_event_duplicates.fix_error.title'), async () => tap(await fixDuplicates([groupId]), () => {
      deselect(autoFix, groupId);
      startPromise(loadGroup(autoFix));
    }));
  }

  async function fixSelected(): Promise<void> {
    const selected = get(autoFix.selected);
    if (selected.length === 0)
      return;

    await autoFix.actionFailure.run(t('actions.customized_event_duplicates.fix_error.title'), async () => tap(await fixDuplicates(selected), () => {
      set(autoFix.selected, []);
      startPromise(loadGroup(autoFix));
    }));
  }

  async function ignoreSingle(groupId: string): Promise<void> {
    const group = get(modelActiveTab) === DuplicatesTab.MANUAL_REVIEW ? manualReview : autoFix;
    await group.actionFailure.run(t('actions.customized_event_duplicates.mark_non_duplicated_error.title'), async () => tap(await ignoreDuplicates([groupId]), () => {
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

    await group.actionFailure.run(t('actions.customized_event_duplicates.mark_non_duplicated_error.title'), async () => tap(await ignoreDuplicates(selected), () => {
      set(group.selected, []);
      startPromise(loadAllGroups());
    }));
  }

  async function restoreSingle(groupId: string): Promise<void> {
    await ignored.actionFailure.run(t('actions.customized_event_duplicates.unignore_error.title'), async () => tap(await unignoreDuplicates([groupId]), () => {
      deselect(ignored, groupId);
      startPromise(loadAllGroups());
    }));
  }

  async function restoreSelected(): Promise<void> {
    const selected = get(ignored.selected);
    if (selected.length === 0)
      return;

    await ignored.actionFailure.run(t('actions.customized_event_duplicates.unignore_error.title'), async () => tap(await unignoreDuplicates(selected), () => {
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
    autoFixActionFailure: autoFix.actionFailure.failure,
    autoFixError: failureOf(autoFix),
    autoFixLoading: readonly(autoFix.loading),
    autoFixRows: shallowReadonly(autoFix.rows),
    fixSelected,
    fixSingle,
    ignoreSelected,
    ignoreSingle,
    ignoredActionFailure: ignored.actionFailure.failure,
    ignoredError: failureOf(ignored),
    ignoredLoading: readonly(ignored.loading),
    ignoredRows: shallowReadonly(ignored.rows),
    initialize,
    manualReviewActionFailure: manualReview.actionFailure.failure,
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
