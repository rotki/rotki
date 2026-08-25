import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from './use-selection-mode';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { get, set } from '@vueuse/shared';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
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
  selectedEventIds: Readonly<Ref<number[]>>;
}

export function useHistoryEventsSelectionActions(
  options: UseHistoryEventsSelectionActionsOptions,
): HistoryEventsSelectionActions {
  const { t } = useI18n({ useScope: 'global' });
  const { show: showConfirm } = useConfirmStore();

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

  function handleAccountingRuleRefresh(): void {
    // Exit selection mode after successfully creating a rule
    selectionMode.actions.exit();
  }

  /** An acknowledgement-only dialog: there is nothing to confirm, so the callback does nothing. */
  function notify(title: string, message: string): void {
    showConfirm({
      message,
      primaryAction: t('common.actions.ok'),
      singleAction: true,
      title,
    }, () => {});
  }

  /**
   * An accounting rule keys off one event type and subtype pair, so a mixed selection cannot seed one
   * and is rejected rather than silently using the first event's pair.
   */
  function startRuleCreation(selectedIds: number[]): void {
    const selectedEvents = toValue(originalGroups).flat().filter(event =>
      !Array.isArray(event) && selectedIds.includes(event.identifier),
    );

    if (selectedEvents.length === 0) {
      notify(
        t('transactions.events.accounting_rule.error'),
        t('transactions.events.accounting_rule.no_events_found'),
      );
      return;
    }

    const { eventSubtype, eventType } = selectedEvents[0];
    const allSameType = selectedEvents.every(event =>
      event.eventType === eventType && event.eventSubtype === eventSubtype,
    );

    if (!allSameType) {
      notify(
        t('transactions.events.accounting_rule.incompatible_selection'),
        t('transactions.events.accounting_rule.different_types_error'),
      );
      return;
    }

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
      case 'ignore': {
        const selectedEvents = getSelectedEvents();
        set(selectedEventsForIgnore, selectedEvents);
        await ignore(true);
        break;
      }
      case 'unignore': {
        const selectedEvents = getSelectedEvents();
        set(selectedEventsForIgnore, selectedEvents);
        await ignore(false);
        break;
      }
      case 'toggle-mode':
        selectionMode.actions.toggle();
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
    selectedEventIds: shallowReadonly(selectedEventIds),
  };
}
