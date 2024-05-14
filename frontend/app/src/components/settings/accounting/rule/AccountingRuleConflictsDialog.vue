<script lang="ts" setup>
import { z } from 'zod';
import type { ConflictResolution } from '@/types/asset';
import type { Collection } from '@/types/collection';
import type { ConflictResolutionStrategy } from '@/types/common';
import type {
  AccountingRuleConflict,
  AccountingRuleConflictRequestPayload,
  AccountingRuleConflictResolution,
} from '@/types/settings/accounting';
import type { DataTableColumn } from '@rotki/ui-library-compat';

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'refresh'): void;
}>();

const close = () => emit('close');

const { getAccountingRulesConflicts, resolveAccountingRuleConflicts } = useAccountingSettings();

const { t } = useI18n();

const { state, isLoading, fetchData, setPage, pagination } = usePaginationFilters<
  AccountingRuleConflict,
  AccountingRuleConflictRequestPayload,
  AccountingRuleConflict,
  Collection<AccountingRuleConflict>
>(
  null,
  true,
  () => ({
    matchers: computed(() => []),
    filters: ref(undefined),
    updateFilter: () => {},
    RouteFilterSchema: z.object({}),
  }),
  getAccountingRulesConflicts,
);

onMounted(() => {
  fetchData();
});

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: `${t('accounting_settings.rule.labels.event_type')} - \n${t(
      'accounting_settings.rule.labels.event_subtype',
    )}`,
    key: 'eventTypeAndSubtype',
    class: 'whitespace-pre-line !text-sm',
  },
  {
    label: t('transactions.events.form.resulting_combination.label'),
    key: 'resultingCombination',
    class: '!text-sm',
  },
  {
    label: t('common.counterparty'),
    key: 'counterparty',
    class: 'border-r border-default !text-sm',
    cellClass: 'border-r border-default',
  },
  {
    label: t('accounting_settings.rule.labels.taxable'),
    key: 'taxable',
    class: 'px-2 max-w-[7.5rem] whitespace-normal font-medium !text-sm',
    cellClass: 'px-0 py-2',
  },
  {
    label: t('accounting_settings.rule.labels.count_entire_amount_spend'),
    key: 'countEntireAmountSpend',
    class: 'px-2 max-w-[7.5rem] whitespace-normal font-medium !text-sm',
    align: 'center',
    cellClass: 'px-0 py-2',
  },
  {
    label: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
    key: 'countCostBasisPnl',
    class: 'px-2 max-w-[7.5rem] whitespace-normal font-medium !text-sm',
    align: 'center',
    cellClass: 'px-0 py-2',
  },
  {
    label: t('accounting_settings.rule.labels.accounting_treatment'),
    key: 'accountingTreatment',
    class: 'max-w-[7.5rem] whitespace-normal font-medium !text-sm',
    cellClass: 'px-0 py-2',
    align: 'center',
  },
  {
    label: t('accounting_settings.rule.conflicts.labels.choose_version'),
    key: 'actions',
    class: '!text-sm w-px',
    cellClass: 'pl-0',
    align: 'center',
  },
]);

const { historyEventTypesData, historyEventSubTypesData, getEventTypeData } = useHistoryEventMappings();

function getHistoryEventTypeName(eventType: string): string {
  return get(historyEventTypesData).find(item => item.identifier === eventType)
    ?.label ?? toSentenceCase(eventType);
}

function getHistoryEventSubTypeName(eventSubtype: string): string {
  return get(historyEventSubTypesData).find(item => item.identifier === eventSubtype)
    ?.label ?? toSentenceCase(eventSubtype);
}

function getType(eventType: string, eventSubtype: string) {
  return get(
    getEventTypeData({
      eventType,
      eventSubtype,
    }),
  );
}

function diffClass(localSetting: boolean | string, remoteSetting: boolean | string) {
  if (localSetting !== remoteSetting)
    return 'bg-rui-error-lighter/[0.2]';

  return '';
}

const resolution: Ref<ConflictResolution> = ref({});
const resolutionLength = computed(() => Object.keys(get(resolution)).length);

const solveAllUsing = ref<ConflictResolutionStrategy>();

const { setMessage } = useMessageStore();

const loading: Ref<boolean> = ref(false);

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
      title: t('accounting_settings.rule.conflicts.error.title'),
      description: t('accounting_settings.rule.conflicts.error.description', {
        error: result.message,
      }),
      success: false,
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
      <div
        class="flex justify-end items-center gap-8 border border-default rounded p-4 mb-4"
      >
        <RuiCheckbox
          :value="!!solveAllUsing"
          color="primary"
          hide-details
          @input="solveAllUsing = $event ? 'local' : undefined"
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
          <template #default>
            <RuiButton
              value="local"
              @click="solveAllUsing = 'local'"
            >
              {{ t('conflict_dialog.keep_local') }}
            </RuiButton>
            <RuiButton
              value="remote"
              @click="solveAllUsing = 'remote'"
            >
              {{ t('conflict_dialog.keep_remote') }}
            </RuiButton>
          </template>
        </RuiButtonGroup>
      </div>

      <div class="text-caption pt-4 pb-1">
        <i18n
          v-if="!solveAllUsing"
          path="conflict_dialog.hint"
          tag="span"
        >
          <template #conflicts>
            <span class="font-medium"> {{ total }} </span>
          </template>
          <template #remaining>
            <span class="font-medium"> {{ remaining }} </span>
          </template>
        </i18n>
        <i18n
          v-else
          path="conflict_dialog.resolve_all_hint"
          tag="span"
        >
          <template #source>
            <span class="font-medium">{{ solveAllUsing }}</span>
          </template>
        </i18n>
      </div>

      <CollectionHandler
        :collection="state"
        class="pb-4"
        @set-page="setPage($event)"
      >
        <template #default="{ data }">
          <RuiDataTable
            :cols="tableHeaders"
            :loading="isLoading"
            :pagination.sync="pagination"
            :pagination-modifiers="{ external: true }"
            :rows="data"
            disable-floating-header
            mobile-breakpoint="0"
            outlined
            row-attr="identifier"
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
                      name="information-line"
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
                      name="information-line"
                      size="18"
                    />
                    {{
                      t(
                        'accounting_settings.rule.labels.count_entire_amount_spend',
                      )
                    }}
                  </div>
                </template>
                {{
                  t(
                    'accounting_settings.rule.labels.count_entire_amount_spend_subtitle',
                  )
                }}
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
                      name="information-line"
                      size="18"
                    />
                    {{
                      t('accounting_settings.rule.labels.count_cost_basis_pnl')
                    }}
                  </div>
                </template>
                {{
                  t(
                    'accounting_settings.rule.labels.count_cost_basis_pnl_subtitle',
                  )
                }}
              </RuiTooltip>
            </template>
            <template #item.eventTypeAndSubtype="{ row }">
              <div>{{ getHistoryEventTypeName(row.localData.eventType) }} -</div>
              <div>{{ getHistoryEventSubTypeName(row.localData.eventSubtype) }}</div>
            </template>
            <template #item.resultingCombination="{ row }">
              <HistoryEventTypeCombination

                :type="
                  getType(
                    row.localData.eventType,
                    row.localData.eventSubtype,
                  )
                "
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
              <div class="w-full flex flex-col items-center justify-center">
                <AccountingRuleWithLinkedSettingDisplay
                  :class="
                    diffClass(
                      row.localData.taxable.value,
                      row.remoteData.taxable.value,
                    )
                  "
                  :item="row.localData.taxable"
                  identifier="taxable"
                />
                <RuiDivider class="w-full my-2" />
                <AccountingRuleWithLinkedSettingDisplay
                  :class="
                    diffClass(
                      row.localData.taxable.value,
                      row.remoteData.taxable.value,
                    )
                  "
                  :item="row.remoteData.taxable"
                  identifier="taxable"
                />
              </div>
            </template>
            <template #item.countEntireAmountSpend="{ row }">
              <div class="w-full flex flex-col items-center justify-center">
                <AccountingRuleWithLinkedSettingDisplay
                  :class="
                    diffClass(
                      row.localData.taxable.value,
                      row.remoteData.taxable.value,
                    )
                  "
                  :item="row.localData.countEntireAmountSpend"
                  identifier="countEntireAmountSpend"
                />
                <RuiDivider class="w-full my-2" />
                <AccountingRuleWithLinkedSettingDisplay
                  :class="
                    diffClass(
                      row.localData.taxable.value,
                      row.remoteData.taxable.value,
                    )
                  "
                  :item="row.remoteData.countEntireAmountSpend"
                  identifier="countEntireAmountSpend"
                />
              </div>
            </template>
            <template #item.countCostBasisPnl="{ row }">
              <div class="w-full flex flex-col items-center justify-center">
                <AccountingRuleWithLinkedSettingDisplay
                  :class="
                    diffClass(
                      row.localData.countCostBasisPnl.value,
                      row.remoteData.countCostBasisPnl.value,
                    )
                  "
                  :item="row.localData.countCostBasisPnl"
                  identifier="countCostBasisPnl"
                />
                <RuiDivider class="w-full my-2" />
                <AccountingRuleWithLinkedSettingDisplay
                  :class="
                    diffClass(
                      row.localData.countCostBasisPnl.value,
                      row.remoteData.countCostBasisPnl.value,
                    )
                  "
                  :item="row.remoteData.countCostBasisPnl"
                  identifier="countCostBasisPnl"
                />
              </div>
            </template>
            <template #item.accountingTreatment="{ row }">
              <div class="w-full flex flex-col items-center justify-center">
                <BadgeDisplay
                  v-if="row.localData.accountingTreatment"
                  :class="
                    diffClass(
                      row.localData.accountingTreatment,
                      row.remoteData.accountingTreatment,
                    )
                  "
                >
                  {{ row.localData.accountingTreatment }}
                </BadgeDisplay>
                <span v-else>-</span>
                <RuiDivider class="w-full my-2" />
                <BadgeDisplay
                  v-if="row.remoteData.accountingTreatment"
                  :class="
                    diffClass(
                      row.localData.accountingTreatment,
                      row.remoteData.accountingTreatment,
                    )
                  "
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
                <template #default>
                  <RuiButton
                    class="w-full"
                    value="local"
                  >
                    {{ t('conflict_dialog.action.local') }}
                  </RuiButton>
                  <RuiButton
                    class="w-full"
                    value="remote"
                  >
                    {{ t('conflict_dialog.action.remote') }}
                  </RuiButton>
                </template>
              </RuiButtonGroup>
            </template>
          </RuiDataTable>
        </template>
      </CollectionHandler>
    </template>
  </BigDialog>
</template>
