import type { ComputedRef, Ref } from 'vue';
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
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

  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const { notify } = useNotificationDispatcher();

  const {
    autoFixGroupIds,
    confirmAndFixDuplicate,
    confirmAndMarkNonDuplicated,
    confirmAndRestore,
    fetchCustomizedEventDuplicates,
    fetchDuplicateEvents,
    ignoredGroupIds,
    manualReviewGroupIds,
  } = useCustomizedEventDuplicates();

  const modelActiveTab = shallowRef<number>(DuplicatesTab.AUTO_FIX);

  const autoFix: DuplicateGroup = {
    groupIds: autoFixGroupIds,
    loading: shallowRef<boolean>(false),
    rows: ref<DuplicateRow[]>([]),
    selected: ref<string[]>([]),
  };

  const manualReview: DuplicateGroup = {
    groupIds: manualReviewGroupIds,
    loading: shallowRef<boolean>(false),
    rows: ref<DuplicateRow[]>([]),
    selected: ref<string[]>([]),
  };

  const ignored: DuplicateGroup = {
    groupIds: ignoredGroupIds,
    loading: shallowRef<boolean>(false),
    rows: ref<DuplicateRow[]>([]),
    selected: ref<string[]>([]),
  };

  async function loadGroup(group: DuplicateGroup): Promise<void> {
    set(group.loading, true);
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
      notify({
        display: true,
        message: t('actions.customized_event_duplicates.fetch_events_error.description', { error: getErrorMessage(error) }),
        severity: Severity.ERROR,
        title: t('actions.customized_event_duplicates.fetch_events_error.title'),
      });
    }
    finally {
      set(group.loading, false);
    }
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
    autoFixLoading: readonly(autoFix.loading),
    autoFixRows: shallowReadonly(autoFix.rows),
    fixSelected,
    fixSingle,
    ignoreSelected,
    ignoreSingle,
    ignoredLoading: readonly(ignored.loading),
    ignoredRows: shallowReadonly(ignored.rows),
    initialize,
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
