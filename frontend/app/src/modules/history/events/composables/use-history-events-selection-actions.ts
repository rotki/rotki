import type { Ref } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from './use-selection-mode';
import type { HistoryEventRow } from '@/types/history/events/schemas';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import { get, set } from '@vueuse/shared';
import { useConfirmStore } from '@/store/confirm';

interface UseHistoryEventsSelectionActionsOptions {
  deletion: {
    deleteSelected: () => Promise<void>;
  };
  originalGroups: Ref<HistoryEventRow[]>;
  selectionMode: UseHistoryEventsSelectionModeReturn;
}

export interface HistoryEventsSelectionActions {
  accountingRuleToEdit: Ref<AccountingRuleEntry | undefined>;
  handleAccountingRuleRefresh: () => void;
  handleSelectionAction: (action: string) => Promise<void>;
  selectedEventIds: Ref<number[]>;
}

export function useHistoryEventsSelectionActions(
  options: UseHistoryEventsSelectionActionsOptions,
): HistoryEventsSelectionActions {
  const { t } = useI18n({ useScope: 'global' });
  const { show: showConfirm } = useConfirmStore();

  const { deletion, originalGroups, selectionMode } = options;

  const accountingRuleToEdit = ref<AccountingRuleEntry | undefined>();
  const selectedEventIds = ref<number[]>([]);

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
        set(accountingRuleToEdit, {
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
      case 'toggle-mode':
        selectionMode.actions.toggle();
        break;
      case 'exit':
        selectionMode.actions.exit();
        break;
      case 'toggle-all':
        selectionMode.actions.toggleAll();
        break;
    }
  }

  return {
    accountingRuleToEdit,
    handleAccountingRuleRefresh,
    handleSelectionAction,
    selectedEventIds,
  };
}
