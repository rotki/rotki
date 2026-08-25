import type { ComputedRef, Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';

export interface UseHistoryEventsFiltersChipsOptions {
  /** The groups the URL asks the table to show, if any. */
  groupIdentifiers: () => string[] | undefined;
  /** Which duplicate bucket those groups came from. */
  duplicateHandlingStatus: () => DuplicateHandlingStatus | undefined;
  /** Called when the table has to reload, after a fix or a manual refresh. */
  onRefresh: () => void;
}

export interface UseHistoryEventsFiltersChipsReturn {
  /** Whether the missing-acquisition chip has a filter to show. */
  showMissingAcquisition: ComputedRef<boolean>;
  /** Whether the negative-balance chip has a filter to show. */
  showNegativeBalance: ComputedRef<boolean>;
  /** Whether the accounting-divergence chip has a filter to show. */
  showAccountingEvent: ComputedRef<boolean>;
  /** Whether the duplicate chip has groups to show. */
  showDuplicates: ComputedRef<boolean>;
  /** Whether the shown duplicates are the bucket that can be fixed automatically. */
  isAutoFixable: ComputedRef<boolean>;
  /** The duplicate chip's own label, which names the bucket. */
  duplicateChipText: ComputedRef<string>;
  /** Whether the backend's duplicates have moved on from what the URL asks for. */
  hasDuplicateChanges: ComputedRef<boolean>;
  /** Whether nothing the URL asks for is a duplicate any more. */
  allDuplicatesResolved: ComputedRef<boolean>;
  /** How the drift from the URL is described to the user. */
  duplicateChangesMessage: ComputedRef<string>;
  /** Whether a fix is in flight. */
  fixLoading: Ref<boolean>;
  /** Drop the missing-acquisition filter from the URL. */
  removeMissingAcquisitionParam: () => void;
  /** Drop the negative-balance filter, and the group it targets, from the URL. */
  removeNegativeBalanceParam: () => void;
  /** Drop the accounting-divergence filter, and the group it targets, from the URL. */
  removeAccountingEventParam: () => void;
  /** Drop the duplicate filter from the URL. */
  removeDuplicateEventsParam: () => void;
  /** Ask for confirmation, then fix every duplicate the chip is showing. */
  confirmFixDuplicate: () => void;
  /** Re-point the URL at what is still a duplicate, or drop the filter when nothing is. */
  refreshDuplicateView: () => void;
}

/**
 * The chips above the events table: what each one is showing, and what closing or
 * acting on it does to the URL.
 *
 * Only the duplicate chip has depth: the URL pins a set of groups while the backend keeps
 * re-deciding which groups are duplicates, so the chip describes the drift between the two and
 * lets the user re-point the URL at the current answer.
 */
export function useHistoryEventsFiltersChips(
  options: UseHistoryEventsFiltersChipsOptions,
): UseHistoryEventsFiltersChipsReturn {
  const { duplicateHandlingStatus, groupIdentifiers, onRefresh } = options;

  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const route = useRoute();
  const { show } = useConfirmStore();
  const {
    autoFixGroupIds,
    fixDuplicates,
    fixLoading,
    manualReviewGroupIds,
  } = useCustomizedEventDuplicates();

  const showMissingAcquisition = computed<boolean>(() => !!get(route).query.missingAcquisitionIdentifier);

  const showNegativeBalance = computed<boolean>(() => !!get(route).query.highlightedNegativeBalanceEvent);

  const showAccountingEvent = computed<boolean>(() => !!get(route).query.highlightedAccountingEvent);

  const showDuplicates = computed<boolean>(() => {
    const ids = groupIdentifiers();
    return !!ids && ids.length > 0;
  });

  const isAutoFixable = computed<boolean>(() => duplicateHandlingStatus() === DuplicateHandlingStatus.AUTO_FIX);

  const duplicateChipText = computed<string>(() => {
    if (get(isAutoFixable))
      return t('customized_event_duplicates.chips.viewing_auto_fixable');
    return t('customized_event_duplicates.chips.viewing_manual_review');
  });

  // Track the current valid group IDs from the composable
  const currentValidGroupIds = computed<string[]>(() =>
    get(isAutoFixable) ? get(autoFixGroupIds) : get(manualReviewGroupIds),
  );

  // Calculate the difference between URL params and current valid IDs
  const duplicateChanges = computed<{ resolved: number; added: number; remaining: string[] }>(() => {
    const urlIds = groupIdentifiers() ?? [];
    const validIds = get(currentValidGroupIds);

    if (urlIds.length === 0)
      return { added: 0, remaining: [], resolved: 0 };

    const remaining = urlIds.filter(id => validIds.includes(id));
    const resolved = urlIds.length - remaining.length;
    const added = validIds.filter(id => !urlIds.includes(id)).length;

    return { added, remaining, resolved };
  });

  const hasDuplicateChanges = computed<boolean>(() => {
    const { added, resolved } = get(duplicateChanges);
    return resolved > 0 || added > 0;
  });

  const allDuplicatesResolved = computed<boolean>(() => {
    const { remaining } = get(duplicateChanges);
    return get(showDuplicates) && remaining.length === 0;
  });

  const duplicateChangesMessage = computed<string>(() => {
    const { added, resolved } = get(duplicateChanges);

    if (get(allDuplicatesResolved))
      return t('customized_event_duplicates.chips.all_resolved');

    const messages: string[] = [];
    if (resolved > 0)
      messages.push(t('customized_event_duplicates.chips.resolved_count', { count: resolved }));

    if (added > 0)
      messages.push(t('customized_event_duplicates.chips.added_count', { count: added }));

    return messages.join(' ');
  });

  function pushWithout(...keys: string[]): void {
    const query = { ...get(route).query };
    for (const key of keys)
      delete query[key];
    startPromise(router.push({ query }));
  }

  function removeMissingAcquisitionParam(): void {
    pushWithout('missingAcquisitionIdentifier');
  }

  function removeNegativeBalanceParam(): void {
    pushWithout('highlightedNegativeBalanceEvent', 'targetGroupIdentifier');
  }

  function removeAccountingEventParam(): void {
    pushWithout('highlightedAccountingEvent', 'targetGroupIdentifier');
  }

  function removeDuplicateEventsParam(): void {
    pushWithout('groupIdentifiers', 'duplicateHandlingStatus');
  }

  async function fixDuplicateEvent(): Promise<void> {
    const ids = groupIdentifiers();
    if (!ids || ids.length === 0)
      return;

    const result = await fixDuplicates(ids);
    if (result.success) {
      removeDuplicateEventsParam();
      onRefresh();
    }
  }

  function confirmFixDuplicate(): void {
    const count = groupIdentifiers()?.length ?? 0;
    show({
      message: t('customized_event_duplicates.actions.fix_selected_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('customized_event_duplicates.actions.fix_selected'),
    }, async () => fixDuplicateEvent());
  }

  function refreshDuplicateView(): void {
    const validIds = get(currentValidGroupIds);

    if (validIds.length === 0) {
      removeDuplicateEventsParam();
    }
    else {
      const query = { ...get(route).query, groupIdentifiers: validIds.join(',') };
      startPromise(router.replace({ query }));
    }
    onRefresh();
  }

  return {
    allDuplicatesResolved,
    confirmFixDuplicate,
    duplicateChangesMessage,
    duplicateChipText,
    fixLoading,
    hasDuplicateChanges,
    isAutoFixable,
    refreshDuplicateView,
    removeAccountingEventParam,
    removeDuplicateEventsParam,
    removeMissingAcquisitionParam,
    removeNegativeBalanceParam,
    showAccountingEvent,
    showDuplicates,
    showMissingAcquisition,
    showNegativeBalance,
  };
}
