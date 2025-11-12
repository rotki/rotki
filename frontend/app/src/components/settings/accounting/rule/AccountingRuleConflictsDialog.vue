<script lang="ts" setup>
import type { DataTableColumn } from '@rotki/ui-library';
import type { ConflictResolution } from '@/types/asset';
import type { ConflictResolutionStrategy } from '@/types/common';
import type {
  AccountingRuleConflict,
  AccountingRuleConflictRequestPayload,
  AccountingRuleConflictResolution,
  AccountingTreatment,
} from '@/types/settings/accounting';
import { toSentenceCase } from '@rotki/common';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import CounterpartyDisplay from '@/components/history/CounterpartyDisplay.vue';
import HistoryEventTypeCombination from '@/components/history/events/HistoryEventTypeCombination.vue';
import AccountingRuleWithLinkedSettingDisplay
  from '@/components/settings/accounting/rule/AccountingRuleWithLinkedSettingDisplay.vue';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useAccountingSettings } from '@/composables/settings/accounting';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useMessageStore } from '@/store/message';
import { getCollectionData } from '@/utils/collection';

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'refresh'): void;
}>();

const close = () => emit('close');

const { getAccountingRulesConflicts, resolveAccountingRuleConflicts } = useAccountingSettings();

const { t } = useI18n({ useScope: 'global' });

const { fetchData, isLoading, pagination, state } = usePaginationFilters<
  AccountingRuleConflict,
  AccountingRuleConflictRequestPayload
>(getAccountingRulesConflicts, {
  history: 'router',
});

onMounted(() => {
  fetchData();
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

function diffClass(
  localSetting: boolean | string | AccountingTreatment | null,
  remoteSetting: boolean | string | AccountingTreatment | null,
) {
  if (localSetting !== remoteSetting)
    return 'bg-rui-error-lighter/[0.1]';

  return '';
}

const resolution = ref<ConflictResolution>({});
const resolutionLength = computed(() => Object.keys(get(resolution)).length);

const solveAllUsing = ref<ConflictResolutionStrategy>();

const { setMessage } = useMessageStore();

const loading = ref<boolean>(false);

const { total } = getCollectionData<AccountingRuleConflict>(state);

const remaining = computed(() => {
  const resolved = get(resolutionLength);
  return get(total) - resolved;
});

const valid = computed(() => !!get(solveAllUsing) || get(resolutionLength) > 0);

async function save() {
  set(loading, true);
  const resolutionVal = get(resolution);
  const solveAllVal = get(solveAllUsing);

  let payload: AccountingRuleConflictResolution;
  if (solveAllVal) {
    payload = { solveAllUsing: solveAllVal };
  }
  else {
    const conflicts = Object.keys(resolutionVal).map(localId => ({
      localId,
      solveUsing: resolutionVal[localId],
    }));

    payload = { conflicts };
  }

  const result = await resolveAccountingRuleConflicts(payload);

  if (result.success) {
    emit('refresh');
    close();
  }
  else {
    setMessage({
      description: t('accounting_settings.rule.conflicts.error.description', {
        error: result.message,
      }),
      success: false,
      title: t('accounting_settings.rule.conflicts.error.title'),
    });
  }

  set(loading, false);
}
</script>

<template>
  <BigDialog
    :action-disabled="!valid"
    display
    :loading="loading"
    :persistent="resolutionLength > 0"
    :primary-action="t('common.actions.save')"
    :title="t('accounting_settings.rule.conflicts.title')"
    max-width="75rem"
    @cancel="close()"
    @confirm="save()"
  >
    <template #default="{ wrapper }">
      <div class="flex justify-end items-center gap-8 border border-default rounded p-4 mb-4">
        <RuiCheckbox
          :model-value="!!solveAllUsing"
          color="primary"
          hide-details
          @update:model-value="solveAllUsing = $event ? 'local' : undefined"
        >
          {{ t('conflict_dialog.all_buttons_description') }}
        </RuiCheckbox>
        <RuiButtonGroup
          v-model="solveAllUsing"
          :disabled="!solveAllUsing"
          color="primary"
          required
          variant="outlined"
        >
          <RuiButton
            model-value="local"
            @click="solveAllUsing = 'local'"
          >
            {{ t('conflict_dialog.keep_local') }}
          </RuiButton>
          <RuiButton
            model-value="remote"
            @click="solveAllUsing = 'remote'"
          >
            {{ t('conflict_dialog.keep_remote') }}
          </RuiButton>
        </RuiButtonGroup>
      </div>

      <div class="text-caption pt-4 pb-1">
        <i18n-t
          v-if="!solveAllUsing"
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
            <span class="font-medium">{{ solveAllUsing }}</span>
          </template>
        </i18n-t>
      </div>

      <RuiDataTable
        v-model:pagination.external="pagination"
        class="pb-4"
        :cols="tableHeaders"
        :loading="isLoading"
        :rows="state.data"
        disable-floating-header
        mobile-breakpoint="0"
        outlined
        row-attr="localId"
        :scroller="wrapper"
      >
        <template #header.taxable>
          <RuiTooltip
            :open-delay="400"
            :popper="{ placement: 'top' }"
            class="flex items-center"
            tooltip-class="max-w-[10rem]"
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
            :popper="{ placement: 'top' }"
            class="flex items-center"
            tooltip-class="max-w-[10rem]"
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
            :popper="{ placement: 'top' }"
            class="flex items-center"
            tooltip-class="max-w-[10rem]"
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
            :class="diffClass(row.localData.taxable.value, row.remoteData.taxable.value)"
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
            v-model="resolution[row.localId]"
            :disabled="!!solveAllUsing"
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
