<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/types/collection';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import { toSentenceCase } from '@rotki/common';
import RowActions from '@/components/helper/RowActions.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import CounterpartyDisplay from '@/components/history/CounterpartyDisplay.vue';
import HistoryEventTypeCombination from '@/components/history/events/HistoryEventTypeCombination.vue';
import AccountingRuleEventsDialog from '@/components/settings/accounting/rule/AccountingRuleEventsDialog.vue';
import AccountingRuleWithLinkedSettingDisplay from '@/components/settings/accounting/rule/AccountingRuleWithLinkedSettingDisplay.vue';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';

interface AccountingRuleTableProps {
  state: Collection<AccountingRuleEntry>;
  pagination: TablePaginationData;
  isLoading: boolean;
  isCustom: boolean;
}

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const props = defineProps<AccountingRuleTableProps>();

const emit = defineEmits<{
  'set-page': [page: number];
  'delete-click': [item: AccountingRuleEntry];
  'edit-click': [item: AccountingRuleEntry];
}>();

const { t } = useI18n({ useScope: 'global' });

const selectedEventIds = ref<number[]>([]);
const eventsDialogOpen = ref<boolean>(false);

const cols = computed<DataTableColumn<AccountingRuleEntry>[]>(() => {
  const baseColumns: DataTableColumn<AccountingRuleEntry>[] = [];

  // Regular view columns
  baseColumns.push(
    {
      cellClass: 'py-4',
      class: 'whitespace-pre-line',
      key: 'eventTypeAndSubtype',
      label: `${t('accounting_settings.rule.labels.event_type')} - \n${t(
        'accounting_settings.rule.labels.event_subtype',
      )}`,
    },
    {
      key: 'resultingCombination',
      label: t('transactions.events.form.resulting_combination.label'),
    },
    {
      cellClass: props.isCustom ? '' : 'border-r border-default',
      class: props.isCustom ? '' : 'border-r border-default',
      key: 'counterparty',
      label: t('common.counterparty'),
    },
  );

  // For special rules view (custom rules with eventIds), show event IDs instead of event type/subtype/counterparty
  if (props.isCustom) {
    baseColumns.push({
      cellClass: 'py-4 border-r border-default',
      class: 'border-r border-default',
      key: 'eventIds',
      label: t('accounting_settings.rule.labels.event_ids'),
    });
  }

  // Common columns for both views
  baseColumns.push(
    {
      align: 'center',
      class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
      key: 'taxable',
      label: t('accounting_settings.rule.labels.taxable'),
    },
    {
      align: 'center',
      class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
      key: 'countEntireAmountSpend',
      label: t('accounting_settings.rule.labels.count_entire_amount_spend'),
    },
    {
      align: 'center',
      class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
      key: 'countCostBasisPnl',
      label: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
    },
    {
      class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
      key: 'accountingTreatment',
      label: t('accounting_settings.rule.labels.accounting_treatment'),
    },
    {
      align: 'center',
      key: 'actions',
      label: t('common.actions_text'),
      width: '1px',
    },
  );

  return baseColumns;
});

const { getEventTypeData, historyEventSubTypesData, historyEventTypesData } = useHistoryEventMappings();

function getHistoryEventTypeName(eventType: string): string {
  return get(historyEventTypesData).find(item => item.identifier === eventType)?.label ?? toSentenceCase(eventType);
}

function getHistoryEventSubTypeName(eventSubtype: string): string {
  return (
    get(historyEventSubTypesData).find(item => item.identifier === eventSubtype)?.label
    ?? toSentenceCase(eventSubtype)
  );
}

function getType(eventType: string, eventSubtype: string) {
  return get(
    getEventTypeData({
      eventSubtype,
      eventType,
    }),
  );
}

function openEventsDialog(eventIds: number[]) {
  set(selectedEventIds, eventIds);
  set(eventsDialogOpen, true);
}
</script>

<template>
  <RuiDataTable
    v-model:pagination.external="paginationModel"
    outlined
    :rows="state.data"
    :cols="cols"
    :loading="isLoading"
    row-attr="identifier"
  >
    <template #header.taxable>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="flex items-center h-full"
        tooltip-class="max-w-[10rem]"
      >
        <template #activator>
          <div class="flex items-center text-left gap-2">
            <RuiIcon
              class="shrink-0"
              size="18"
              name="lu-info"
            />
            {{ t('accounting_settings.rule.labels.taxable') }}
          </div>
        </template>
        {{ t('accounting_settings.rule.labels.taxable_subtitle') }}
      </RuiTooltip>
    </template>
    <template #header.countEntireAmountSpend>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="flex items-center"
        tooltip-class="max-w-[10rem]"
      >
        <template #activator>
          <div class="flex items-center text-left gap-2">
            <RuiIcon
              class="shrink-0"
              size="18"
              name="lu-info"
            />
            {{ t('accounting_settings.rule.labels.count_entire_amount_spend') }}
          </div>
        </template>
        {{ t('accounting_settings.rule.labels.count_entire_amount_spend_subtitle') }}
      </RuiTooltip>
    </template>
    <template #header.countCostBasisPnl>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="flex items-center"
        tooltip-class="max-w-[10rem]"
      >
        <template #activator>
          <div class="flex items-center text-left gap-2">
            <RuiIcon
              class="shrink-0"
              size="18"
              name="lu-info"
            />
            {{ t('accounting_settings.rule.labels.count_cost_basis_pnl') }}
          </div>
        </template>
        {{ t('accounting_settings.rule.labels.count_cost_basis_pnl_subtitle') }}
      </RuiTooltip>
    </template>
    <template #header.accountingTreatment>
      <div class="max-w-[5rem] text-sm whitespace-normal font-medium">
        {{ t('accounting_settings.rule.labels.accounting_treatment') }}
      </div>
    </template>
    <template #item.eventTypeAndSubtype="{ row }">
      <div>{{ getHistoryEventTypeName(row.eventType) }} -</div>
      <div>{{ getHistoryEventSubTypeName(row.eventSubtype) }}</div>
    </template>
    <template #item.resultingCombination="{ row }">
      <HistoryEventTypeCombination
        :type="getType(row.eventType, row.eventSubtype)"
        show-label
      />
    </template>
    <template #item.counterparty="{ row }">
      <CounterpartyDisplay
        v-if="row.counterparty"
        :counterparty="row.counterparty"
      />
      <span v-else>-</span>
    </template>
    <template #item.taxable="{ row }">
      <AccountingRuleWithLinkedSettingDisplay
        identifier="taxable"
        :item="row.taxable"
      />
    </template>
    <template #item.countEntireAmountSpend="{ row }">
      <AccountingRuleWithLinkedSettingDisplay
        identifier="countEntireAmountSpend"
        :item="row.countEntireAmountSpend"
      />
    </template>
    <template #item.countCostBasisPnl="{ row }">
      <AccountingRuleWithLinkedSettingDisplay
        identifier="countCostBasisPnl"
        :item="row.countCostBasisPnl"
      />
    </template>
    <template #item.accountingTreatment="{ row }">
      <BadgeDisplay v-if="row.accountingTreatment">
        {{ row.accountingTreatment }}
      </BadgeDisplay>
      <span v-else>-</span>
    </template>
    <template #item.eventIds="{ row }">
      <div class="flex items-center gap-2">
        <span>{{ row.eventIds?.length || 0 }} {{ t('common.events') }}</span>
        <RuiButton
          v-if="row.eventIds && row.eventIds.length > 0"
          variant="text"
          icon
          @click="openEventsDialog(row.eventIds)"
        >
          <RuiIcon
            name="lu-arrow-right"
            size="16"
          />
        </RuiButton>
      </div>
    </template>
    <template #item.actions="{ row }">
      <RowActions
        :delete-tooltip="t('accounting_settings.rule.delete')"
        :edit-tooltip="t('accounting_settings.rule.edit')"
        @delete-click="emit('delete-click', row)"
        @edit-click="emit('edit-click', row)"
      />
    </template>
  </RuiDataTable>

  <AccountingRuleEventsDialog
    v-if="eventsDialogOpen"
    :event-ids="selectedEventIds"
    @close="eventsDialogOpen = false"
  />
</template>
