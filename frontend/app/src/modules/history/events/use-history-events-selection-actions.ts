import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from './use-selection-mode';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { get, set } from '@vueuse/shared';
import { useHistoryEventsActionFailure } from '@/modules/history/events/use-history-events-action-failure';
import { useIgnore } from '@/modules/history/use-ignore';

interface UseHistoryEventsSelectionActionsOptions {
  /** Deletion handler owned by the caller; `deleteSelected` already knows the current selection and runs its own confirmation. */
  deletion: {
    deleteSelected: () => Promise<void>;
  };
  /**
   * Unfiltered rows the selection ids are resolved against, so an action still finds an event that
   * the displayed rows hide. The page passes a `shallowReadonly` ref, so a write here is a silent
   * no-op. `MaybeRefOrGetter` rather than `Readonly<Ref<T>>` because readonly modifiers are ignored
   * in assignability, so `set()` still compiles against the latter.
   */
  originalGroups: MaybeRefOrGetter<HistoryEventRow[]>;
  /** Invoked after an ignore or unignore succeeds, once selection mode has been exited, to reload the table. */
  refreshCallback: () => Promise<void>;
  /** Selection state and actions; `state.selectedIds` is read to resolve the targets and `actions.exit` is called once an action completes. */
  selectionMode: UseHistoryEventsSelectionModeReturn;
}

export interface IgnoreStatus {
  ignoredCount: number;
  notIgnoredCount: number;
}

interface HistoryEventsSelectionActions {
  modelAccountingRuleToEdit: Ref<AccountingRuleEntry | undefined>;
  handleAccountingRuleRefresh: () => void;
  handleSelectionAction: (action: string) => Promise<void>;
  ignoreStatus: ComputedRef<IgnoreStatus>;
  /** Why the selection cannot seed an accounting rule, or `undefined` when it can (or is empty). */
  ruleCreationBlocker: ComputedRef<string | undefined>;
  selectedEventIds: Readonly<Ref<number[]>>;
}

export function useHistoryEventsSelectionActions(
  options: UseHistoryEventsSelectionActionsOptions,
): HistoryEventsSelectionActions {
  const { t } = useI18n({ useScope: 'global' });
  const { clearActionFailure, reportActionFailure } = useHistoryEventsActionFailure();

  const { deletion, originalGroups, refreshCallback, selectionMode } = options;

  const modelAccountingRuleToEdit = ref<AccountingRuleEntry | undefined>();
  const selectedEventIds = ref<number[]>([]);
  const selectedEventsForIgnore = ref<HistoryEventEntry[]>([]);

  const { ignore } = useIgnore<HistoryEventEntry>(
    { toData: item => item.groupIdentifier },
    selectedEventsForIgnore,
    async () => {
      selectionMode.actions.exit();
      await refreshCallback();
    },
  );

  /**
   * Excludes the selection from accounting, or includes it again, naming a failure above the table.
   *
   * @param ignored - true to exclude, false to include
   */
  async function ignoreSelection(ignored: boolean): Promise<void> {
    clearActionFailure();
    set(selectedEventsForIgnore, getSelectedEvents());
    const status = await ignore(ignored);
    if (!status.success)
      reportActionFailure(ignored ? t('actions.ignore.error.title') : t('actions.unignore.error.title'), status.message);
  }

  function getSelectedEvents(): HistoryEventEntry[] {
    const selectedIds = Array.from(get(selectionMode.state).selectedIds);
    const allEvents = toValue(originalGroups).flat();
    return allEvents.filter(
      (event): event is HistoryEventEntry => !Array.isArray(event) && selectedIds.includes(event.identifier),
    );
  }

  const ignoreStatus = computed<IgnoreStatus>(() => {
    const selectedEvents = getSelectedEvents();
    const ignoredCount = selectedEvents.filter(event => event.ignoredInAccounting).length;
    const notIgnoredCount = selectedEvents.length - ignoredCount;
    return { ignoredCount, notIgnoredCount };
  });

  /**
   * Leaves selection mode once an accounting rule has been created.
   *
   * @remarks
   * The rule reclassifies the selected events, so the selection the user made against the old
   * classification no longer describes anything they would want to act on again.
   */
  function handleAccountingRuleRefresh(): void {
    selectionMode.actions.exit();
  }

  /**
   * An accounting rule keys off one event type and subtype pair, so a mixed selection cannot seed one.
   *
   * @remarks
   * The toolbar disables the action and shows this reason, rather than letting the user press it and
   * then explaining in a dialog. A selection none of whose events is loaded has nothing to seed from.
   */
  const ruleCreationBlocker = computed<string | undefined>(() => {
    if (get(selectionMode.state).selectedIds.size === 0)
      return undefined;

    const selectedEvents = getSelectedEvents();
    if (selectedEvents.length === 0)
      return t('transactions.events.accounting_rule.no_events_found');

    const { eventSubtype, eventType } = selectedEvents[0];
    const allSameType = selectedEvents.every(event =>
      event.eventType === eventType && event.eventSubtype === eventSubtype,
    );
    return allSameType ? undefined : t('transactions.events.accounting_rule.different_types_error');
  });

  function startRuleCreation(selectedIds: number[]): void {
    const [first] = getSelectedEvents();
    if (!first || get(ruleCreationBlocker) !== undefined)
      return;

    const { eventSubtype, eventType } = first;
    set(selectedEventIds, selectedIds);
    set(modelAccountingRuleToEdit, {
      accountingTreatment: null,
      countCostBasisPnl: { value: false },
      countEntireAmountSpend: { value: false },
      counterparty: null,
      eventSubtype: eventSubtype || '',
      eventType: eventType || '',
      identifier: 0,
      taxable: { value: false },
    });
  }

  async function handleSelectionAction(action: string): Promise<void> {
    const selectedIds = Array.from(get(selectionMode.state).selectedIds);

    switch (action) {
      case 'delete':
        await deletion.deleteSelected();
        break;
      case 'create-rule':
        startRuleCreation(selectedIds);
        break;
      case 'ignore':
        await ignoreSelection(true);
        break;
      case 'unignore':
        await ignoreSelection(false);
        break;
      case 'toggle-mode':
        selectionMode.actions.toggle();
        break;
      case 'clear':
        selectionMode.actions.clear();
        break;
      case 'exit':
        selectionMode.actions.exit();
        break;
      case 'toggle-all':
        selectionMode.actions.toggleAll();
        break;
      case 'toggle-select-all-matching':
        selectionMode.actions.toggleSelectAllMatching();
        break;
    }
  }

  return {
    modelAccountingRuleToEdit,
    handleAccountingRuleRefresh,
    handleSelectionAction,
    ignoreStatus,
    ruleCreationBlocker,
    selectedEventIds: shallowReadonly(selectedEventIds),
  };
}
