import type { ComputedRef, Ref } from 'vue';
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
  /** Unfiltered rows the selection ids are resolved against, so an action still finds an event that the displayed rows hide. */
  originalGroups: Ref<HistoryEventRow[]>;
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
  selectedEventIds: Ref<number[]>;
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
    const allEvents = get(originalGroups).flat();
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

  async function handleSelectionAction(action: string): Promise<void> {
    const selectedIds = Array.from(get(selectionMode.state).selectedIds);

    switch (action) {
      case 'delete':
        await deletion.deleteSelected();
        break;
      case 'create-rule': {
        // Get all selected events to validate they have the same type/subtype
        const allEvents = get(originalGroups).flat();
        const selectedEvents = allEvents.filter(event =>
          !Array.isArray(event) && selectedIds.includes(event.identifier),
        );

        if (selectedEvents.length === 0) {
          // Show confirmation dialog about no events found
          showConfirm({
            message: t('transactions.events.accounting_rule.no_events_found'),
            primaryAction: t('common.actions.ok'),
            singleAction: true,
            title: t('transactions.events.accounting_rule.error'),
          }, () => {
            // User acknowledged the message
          });
          break;
        }

        // Check if all selected events have the same eventType and eventSubtype
        const firstEvent = selectedEvents[0];
        const firstEventType = firstEvent.eventType;
        const firstEventSubtype = firstEvent.eventSubtype;

        const allSameType = selectedEvents.every(event =>
          event.eventType === firstEventType
          && event.eventSubtype === firstEventSubtype,
        );

        if (!allSameType) {
          // Show confirmation dialog about incompatible selection
          showConfirm({
            message: t('transactions.events.accounting_rule.different_types_error'),
            primaryAction: t('common.actions.ok'),
            singleAction: true,
            title: t('transactions.events.accounting_rule.incompatible_selection'),
          }, () => {
            // User acknowledged the message
          });
          break;
        }

        // All events have the same type/subtype, proceed with rule creation
        set(selectedEventIds, selectedIds);
        // Initialize with the common event type and subtype
        set(modelAccountingRuleToEdit, {
          accountingTreatment: null,
          countCostBasisPnl: { value: false },
          countEntireAmountSpend: { value: false },
          counterparty: null,
          eventSubtype: firstEventSubtype || '',
          eventType: firstEventType || '',
          identifier: 0,
          taxable: { value: false },
        });
        break;
      }
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
    selectedEventIds,
  };
}
