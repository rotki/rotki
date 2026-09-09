<script lang="ts" setup>
import type { DataTableColumn } from '@rotki/ui-library';
import type {
  AccountingRuleConflict,
  AccountingTreatment,
} from '@/modules/settings/types/accounting';
import { getCollectionData } from '@/modules/core/common/data/collection-utils';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventTypeCombination from '@/modules/history/events/HistoryEventTypeCombination.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import AccountingRuleWithLinkedSettingDisplay
  from '@/modules/settings/accounting/rule/AccountingRuleWithLinkedSettingDisplay.vue';
import { useAccountingRuleConflictResolution } from '@/modules/settings/accounting/rule/use-accounting-rule-conflict-resolution';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

const emit = defineEmits<{
  close: [];
  refresh: [];
}>();

const close = (): void => emit('close');

const { t } = useI18n({ useScope: 'global' });

const {
  collection,
  isLoading,
  loading,
  modelResolution,
  modelSolveAllUsing,
  pagination,
  refetch,
  remaining,
  resolutionLength,
  save,
  valid,
} = useAccountingRuleConflictResolution({
  onResolved: (): void => {
    emit('refresh');
    close();
  },
});

onMounted(async () => {
  await refetch();
});

const tableHeaders = computed<DataTableColumn<AccountingRuleConflict>[]>(() => [
  {
    class: 'whitespace-pre-line !text-sm',
    key: 'eventTypeAndSubtype',
    label: `${t('accounting_settings.rule.labels.event_type')} - \n${t(
      'accounting_settings.rule.labels.event_subtype',
    )}`,
  },
  {
    class: '!text-sm',
    key: 'resultingCombination',
    label: t('transactions.events.form.resulting_combination.label'),
  },
  {
    cellClass: 'border-r border-default',
    class: 'border-r border-default !text-sm',
    key: 'counterparty',
    label: t('common.counterparty'),
  },
  {
    cellClass: '!p-0',
    class: 'p-0 max-w-[7.5rem] whitespace-normal font-medium !text-sm',
    key: 'taxable',
    label: t('accounting_settings.rule.labels.taxable'),
  },
  {
    align: 'center',
    cellClass: '!p-0',
    class: 'p-0 max-w-[7.5rem] whitespace-normal font-medium !text-sm',
    key: 'countEntireAmountSpend',
    label: t('accounting_settings.rule.labels.count_entire_amount_spend'),
  },
  {
    align: 'center',
    cellClass: '!p-0',
    class: 'p-0 max-w-[7.5rem] whitespace-normal font-medium !text-sm',
    key: 'countCostBasisPnl',
    label: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
  },
  {
    align: 'center',
    cellClass: '!p-0',
    class: 'p-0 max-w-[7.5rem] whitespace-normal font-medium !text-sm',
    key: 'accountingTreatment',
    label: t('accounting_settings.rule.labels.accounting_treatment'),
  },
  {
    align: 'center',
    cellClass: 'pl-0',
    class: '!text-sm w-px',
    key: 'actions',
    label: t('accounting_settings.rule.conflicts.labels.choose_version'),
  },
]);

const { getEventTypeData, getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

function getType(eventType: string, eventSubtype: string) {
  return get(
    getEventTypeData({
      eventSubtype,
      eventType,
    }),
  );
}

function diffClass(
  localSetting: boolean | string | AccountingTreatment | null,
  remoteSetting: boolean | string | AccountingTreatment | null,
) {
  if (localSetting !== remoteSetting)
    return 'bg-rui-error-lighter/[0.1]';

  return '';
}

const { total } = getCollectionData<AccountingRuleConflict>(collection);
</script>

<template>
  <BigDialog
    :action="{ disabled: !valid, primary: t('common.actions.save') }"
    display
    :layout="{ maxWidth: '75rem' }"
    :loading="loading"
    :persistent="resolutionLength > 0"
    :title="t('accounting_settings.rule.conflicts.title')"
    @cancel="close()"
    @confirm="save()"
  >
    <template #default>
      <div class="flex justify-end items-center gap-8 border border-default rounded p-4 mb-4">
        <RuiCheckbox
          :model-value="!!modelSolveAllUsing"
          color="primary"
          hide-details
          @update:model-value="modelSolveAllUsing = $event ? 'local' : undefined"
        >
          {{ t('conflict_dialog.all_buttons_description') }}
        </RuiCheckbox>
        <RuiButtonGroup
          v-model="modelSolveAllUsing"
          :disabled="!modelSolveAllUsing"
          color="primary"
          required
          variant="outlined"
        >
          <RuiButton
            model-value="local"
            @click="modelSolveAllUsing = 'local'"
          >
            {{ t('conflict_dialog.keep_local') }}
          </RuiButton>
          <RuiButton
            model-value="remote"
            @click="modelSolveAllUsing = 'remote'"
          >
            {{ t('conflict_dialog.keep_remote') }}
          </RuiButton>
        </RuiButtonGroup>
      </div>

      <div class="text-caption pt-4 pb-1">
        <i18n-t
          v-if="!modelSolveAllUsing"
          scope="global"
          keypath="conflict_dialog.hint"
          tag="span"
        >
          <template #conflicts>
            <span class="font-medium"> {{ total }} </span>
          </template>
          <template #remaining>
            <span class="font-medium"> {{ remaining }} </span>
          </template>
        </i18n-t>
        <i18n-t
          v-else
          scope="global"
          keypath="conflict_dialog.resolve_all_hint"
          tag="span"
        >
          <template #source>
            <span class="font-medium">{{ modelSolveAllUsing }}</span>
          </template>
        </i18n-t>
      </div>

      <RuiDataTable
        v-model:pagination.external="pagination"
        class="pb-4"
        :cols="tableHeaders"
        :loading="isLoading"
        :rows="collection.data"
        disable-floating-header
        :mobile-breakpoint="0"
        outlined
        row-attr="localId"
      >
        <template #header.taxable>
          <RuiTooltip
            :open-delay="400"
            :options="{ placement: 'top' }"
            class="flex items-center"
            :class-names="{ tooltip: 'max-w-[10rem]' }"
          >
            <template #activator>
              <div class="flex items-center text-left gap-2">
                <RuiIcon
                  class="shrink-0"
                  name="lu-info"
                  size="18"
                />
                {{ t('accounting_settings.rule.labels.taxable') }}
              </div>
            </template>
            {{ t('accounting_settings.rule.labels.taxable_subtitle') }}
          </RuiTooltip>
        </template>
        <template #header.countEntireAmountSpend>
          <RuiTooltip
            :open-delay="400"
            :options="{ placement: 'top' }"
            class="flex items-center"
            :class-names="{ tooltip: 'max-w-[10rem]' }"
          >
            <template #activator>
              <div class="flex items-center text-left gap-2">
                <RuiIcon
                  class="shrink-0"
                  name="lu-info"
                  size="18"
                />
                {{ t('accounting_settings.rule.labels.count_entire_amount_spend') }}
              </div>
            </template>
            {{ t('accounting_settings.rule.labels.count_entire_amount_spend_subtitle') }}
          </RuiTooltip>
        </template>
        <template #header.countCostBasisPnl>
          <RuiTooltip
            :open-delay="400"
            :options="{ placement: 'top' }"
            class="flex items-center"
            :class-names="{ tooltip: 'max-w-[10rem]' }"
          >
            <template #activator>
              <div class="flex items-center text-left gap-2">
                <RuiIcon
                  class="shrink-0"
                  name="lu-info"
                  size="18"
                />
                {{ t('accounting_settings.rule.labels.count_cost_basis_pnl') }}
              </div>
            </template>
            {{ t('accounting_settings.rule.labels.count_cost_basis_pnl_subtitle') }}
          </RuiTooltip>
        </template>
        <template #item.eventTypeAndSubtype="{ row }">
          <div>{{ getHistoryEventTypeName(row.localData.eventType) }} -</div>
          <div>{{ getHistoryEventSubTypeName(row.localData.eventSubtype) }}</div>
        </template>
        <template #item.resultingCombination="{ row }">
          <HistoryEventTypeCombination
            :type="getType(row.localData.eventType, row.localData.eventSubtype)"
            show-label
          />
        </template>
        <template #item.counterparty="{ row }">
          <CounterpartyDisplay
            v-if="row.localData.counterparty"
            :counterparty="row.localData.counterparty"
          />
          <span v-else>-</span>
        </template>
        <template #item.taxable="{ row }">
          <div
            class="w-full flex flex-col items-center justify-center p-4"
            :class="diffClass(row.localData.taxable.value, row.remoteData.taxable.value)"
          >
            <AccountingRuleWithLinkedSettingDisplay
              :item="row.localData.taxable"
              identifier="taxable"
            />
            <RuiDivider class="w-full my-2" />
            <AccountingRuleWithLinkedSettingDisplay
              :item="row.remoteData.taxable"
              identifier="taxable"
            />
          </div>
        </template>
        <template #item.countEntireAmountSpend="{ row }">
          <div
            class="w-full flex flex-col items-center justify-center p-4"
            :class="diffClass(row.localData.countEntireAmountSpend.value, row.remoteData.countEntireAmountSpend.value)"
          >
            <AccountingRuleWithLinkedSettingDisplay
              :item="row.localData.countEntireAmountSpend"
              identifier="countEntireAmountSpend"
            />
            <RuiDivider class="w-full my-2" />
            <AccountingRuleWithLinkedSettingDisplay
              :item="row.remoteData.countEntireAmountSpend"
              identifier="countEntireAmountSpend"
            />
          </div>
        </template>
        <template #item.countCostBasisPnl="{ row }">
          <div
            class="w-full flex flex-col items-center justify-center p-4"
            :class="diffClass(row.localData.countCostBasisPnl.value, row.remoteData.countCostBasisPnl.value)"
          >
            <AccountingRuleWithLinkedSettingDisplay
              :item="row.localData.countCostBasisPnl"
              identifier="countCostBasisPnl"
            />
            <RuiDivider class="w-full my-2" />
            <AccountingRuleWithLinkedSettingDisplay
              :item="row.remoteData.countCostBasisPnl"
              identifier="countCostBasisPnl"
            />
          </div>
        </template>
        <template #item.accountingTreatment="{ row }">
          <div
            class="w-full flex flex-col items-center justify-center p-4"
            :class="diffClass(row.localData.accountingTreatment, row.remoteData.accountingTreatment)"
          >
            <BadgeDisplay
              v-if="row.localData.accountingTreatment"
            >
              {{ row.localData.accountingTreatment }}
            </BadgeDisplay>
            <span v-else>-</span>
            <RuiDivider class="w-full my-2" />
            <BadgeDisplay
              v-if="row.remoteData.accountingTreatment"
            >
              {{ row.remoteData.accountingTreatment }}
            </BadgeDisplay>
            <span v-else>-</span>
          </div>
        </template>
        <template #item.actions="{ row }">
          <RuiButtonGroup
            v-model="modelResolution[row.localId]"
            :disabled="!!modelSolveAllUsing"
            class="w-full"
            color="primary"
            required
            variant="outlined"
            vertical
          >
            <RuiButton
              class="w-full"
              model-value="local"
            >
              {{ t('conflict_dialog.action.local') }}
            </RuiButton>
            <RuiButton
              class="w-full"
              model-value="remote"
            >
              {{ t('conflict_dialog.action.remote') }}
            </RuiButton>
          </RuiButtonGroup>
        </template>
      </RuiDataTable>
    </template>
  </BigDialog>
</template>
