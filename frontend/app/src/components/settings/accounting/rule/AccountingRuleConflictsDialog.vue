<script setup lang="ts">
import { z } from 'zod';
import { type DataTableHeader } from 'vuetify';
import { type Ref } from 'vue';
import {
  type AccountingRuleConflict,
  type AccountingRuleConflictRequestPayload,
  type AccountingRuleConflictResolution
} from '@/types/settings/accounting';
import { type Collection } from '@/types/collection';
import { type ConflictResolution } from '@/types/asset';
import { type ConflictResolutionStrategy } from '@/types/common';

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'refresh'): void;
}>();

const close = () => emit('close');

const { getAccountingRulesConflicts, resolveAccountingRuleConflicts } =
  useAccountingSettings();

const { t } = useI18n();

const { state, isLoading, options, fetchData, setOptions, setPage } =
  usePaginationFilters<
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
      RouteFilterSchema: z.object({})
    }),
    getAccountingRulesConflicts
  );

onMounted(() => {
  fetchData();
});

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: `${t('accounting_settings.rule.labels.event_type')} - \n${t(
      'accounting_settings.rule.labels.event_subtype'
    )}`,
    value: 'eventTypeAndSubtype',
    class: 'whitespace-break-spaces',
    sortable: false
  },
  {
    text: t('transactions.events.form.resulting_combination.label'),
    value: 'resultingCombination',
    sortable: false
  },
  {
    text: t('accounting_settings.rule.labels.counterparty'),
    value: 'counterparty',
    class: 'border-r border-default',
    sortable: false
  },
  {
    text: t('accounting_settings.rule.labels.taxable'),
    value: 'taxable',
    sortable: false,
    class: 'px-2'
  },
  {
    text: t('accounting_settings.rule.labels.count_entire_amount_spend'),
    value: 'countEntireAmountSpend',
    sortable: false,
    width: '120px',
    class: 'px-2',
    align: 'center'
  },
  {
    text: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
    value: 'countCostBasisPnl',
    sortable: false,
    width: '120px',
    class: 'px-2',
    align: 'center'
  },
  {
    text: t('accounting_settings.rule.labels.accounting_treatment'),
    value: 'accountingTreatment',
    sortable: false
  },
  {
    text: t('accounting_settings.rule.conflicts.labels.choose_version'),
    value: 'actions',
    align: 'center',
    sortable: false
  }
]);

const { historyEventTypesData, historyEventSubTypesData, getEventTypeData } =
  useHistoryEventMappings();

const getHistoryEventTypeName = (eventType: string): string =>
  get(historyEventTypesData).find(item => item.identifier === eventType)
    ?.label ?? toSentenceCase(eventType);

const getHistoryEventSubTypeName = (eventSubtype: string): string =>
  get(historyEventSubTypesData).find(item => item.identifier === eventSubtype)
    ?.label ?? toSentenceCase(eventSubtype);

const getType = (eventType: string, eventSubtype: string) =>
  getEventTypeData({
    eventType,
    eventSubtype
  });

const diffClass = (
  localSetting: boolean | string,
  remoteSetting: boolean | string
) => {
  if (localSetting !== remoteSetting) {
    return 'bg-rui-error-lighter/[0.2]';
  }
  return '';
};

const resolution: Ref<ConflictResolution> = ref({});
const resolutionLength = computed(() => Object.keys(get(resolution)).length);

const { total } = getCollectionData<AccountingRuleConflict>(state);

const remaining = computed(() => {
  const resolved = get(resolutionLength);
  return get(total) - resolved;
});

const valid = computed(() => !!get(solveAllUsing) || get(resolutionLength) > 0);

const solveAllUsing: Ref<ConflictResolutionStrategy | null> = ref(null);

const { setMessage } = useMessageStore();

const loading: Ref<boolean> = ref(false);

const save = async () => {
  set(loading, true);
  const resolutionVal = get(resolution);
  const solveAllVal = get(solveAllUsing);

  let payload: AccountingRuleConflictResolution;
  if (solveAllVal) {
    payload = { solveAllUsing: solveAllVal };
  } else {
    const conflicts = Object.keys(resolutionVal).map(localId => ({
      localId,
      solveUsing: resolutionVal[localId]
    }));

    payload = { conflicts };
  }

  const result = await resolveAccountingRuleConflicts(payload);

  if (result.success) {
    emit('refresh');
    close();
  } else {
    setMessage({
      title: t('accounting_settings.rule.conflicts.error.title'),
      description: t('accounting_settings.rule.conflicts.error.description', {
        error: result.message
      }),
      success: false
    });
  }

  set(loading, false);
};
</script>

<template>
  <BigDialog
    :display="true"
    :title="t('accounting_settings.rule.conflicts.title')"
    :action-disabled="!valid"
    :loading="loading"
    max-width="1200px"
    :persistent="resolutionLength > 0"
    :primary-action="t('common.actions.save')"
    @cancel="close()"
    @confirm="save()"
  >
    <div
      class="flex justify-end items-center gap-8 border border-default rounded p-4 mb-4"
    >
      <RuiCheckbox
        color="primary"
        :value="!!solveAllUsing"
        hide-details
        @input="solveAllUsing = $event ? 'local' : null"
      >
        {{ t('conflict_dialog.all_buttons_description') }}
      </RuiCheckbox>
      <RuiButtonGroup
        v-model="solveAllUsing"
        color="primary"
        required
        variant="outlined"
        :disabled="!solveAllUsing"
      >
        <template #default>
          <RuiButton value="local" @click="solveAllUsing = 'local'">
            {{ t('conflict_dialog.keep_local') }}
          </RuiButton>
          <RuiButton value="remote" @click="solveAllUsing = 'remote'">
            {{ t('conflict_dialog.keep_remote') }}
          </RuiButton>
        </template>
      </RuiButtonGroup>
    </div>

    <div class="text-caption pt-4 pb-1">
      <i18n v-if="!solveAllUsing" path="conflict_dialog.hint" tag="span">
        <template #conflicts>
          <span class="font-medium"> {{ total }} </span>
        </template>
        <template #remaining>
          <span class="font-medium"> {{ remaining }} </span>
        </template>
      </i18n>
      <i18n v-else path="conflict_dialog.resolve_all_hint" tag="span">
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
      <template #default="{ data, itemLength }">
        <DataTable
          :items="data"
          :headers="tableHeaders"
          :loading="isLoading"
          :options="options"
          :server-items-length="itemLength"
          disable-floating-header
          mobile-breakpoint="0"
          @update:options="setOptions($event)"
        >
          <template #header.taxable>
            <RuiTooltip
              :popper="{ placement: 'top' }"
              open-delay="400"
              class="flex items-center"
              tooltip-class="max-w-[10rem]"
            >
              <template #activator>
                <div class="flex items-center text-left gap-2">
                  <RuiIcon class="shrink-0" size="18" name="information-line" />
                  {{ t('accounting_settings.rule.labels.taxable') }}
                </div>
              </template>
              {{ t('accounting_settings.rule.labels.taxable_subtitle') }}
            </RuiTooltip>
          </template>
          <template #header.countEntireAmountSpend>
            <RuiTooltip
              :popper="{ placement: 'top' }"
              open-delay="400"
              class="flex items-center"
              tooltip-class="max-w-[10rem]"
            >
              <template #activator>
                <div class="flex items-center text-left gap-2">
                  <RuiIcon class="shrink-0" size="18" name="information-line" />
                  {{
                    t(
                      'accounting_settings.rule.labels.count_entire_amount_spend'
                    )
                  }}
                </div>
              </template>
              {{
                t(
                  'accounting_settings.rule.labels.count_entire_amount_spend_subtitle'
                )
              }}
            </RuiTooltip>
          </template>
          <template #header.countCostBasisPnl>
            <RuiTooltip
              :popper="{ placement: 'top' }"
              open-delay="400"
              class="flex items-center"
              tooltip-class="max-w-[10rem]"
            >
              <template #activator>
                <div class="flex items-center text-left gap-2">
                  <RuiIcon class="shrink-0" size="18" name="information-line" />
                  {{
                    t('accounting_settings.rule.labels.count_cost_basis_pnl')
                  }}
                </div>
              </template>
              {{
                t(
                  'accounting_settings.rule.labels.count_cost_basis_pnl_subtitle'
                )
              }}
            </RuiTooltip>
          </template>
          <template #body="{ items }">
            <tbody v-for="item in items" :key="item.localId">
              <tr>
                <td rowspan="2">
                  <div>
                    {{ getHistoryEventTypeName(item.localData.eventType) }} -
                  </div>
                  <div>
                    {{
                      getHistoryEventSubTypeName(item.localData.eventSubtype)
                    }}
                  </div>
                </td>
                <td rowspan="2">
                  <HistoryEventTypeCombination
                    :type="
                      getType(
                        item.localData.eventType,
                        item.localData.eventSubtype
                      )
                    "
                    show-label
                  />
                </td>
                <td rowspan="2" class="border-r border-default">
                  <HistoryEventTypeCounterparty
                    v-if="item.counterparty"
                    text
                    :event="{ counterparty: item.counterparty }"
                  />
                  <span v-else>-</span>
                </td>
                <td
                  :class="
                    diffClass(
                      item.localData.taxable.value,
                      item.remoteData.taxable.value
                    )
                  "
                >
                  <AccountingRuleWithLinkedSettingDisplay
                    identifier="taxable"
                    :item="item.localData.taxable"
                  />
                </td>
                <td
                  :class="
                    diffClass(
                      item.localData.taxable.value,
                      item.remoteData.taxable.value
                    )
                  "
                >
                  <AccountingRuleWithLinkedSettingDisplay
                    identifier="countEntireAmountSpend"
                    :item="item.localData.countEntireAmountSpend"
                  />
                </td>
                <td
                  :class="
                    diffClass(
                      item.localData.countCostBasisPnl.value,
                      item.remoteData.countCostBasisPnl.value
                    )
                  "
                >
                  <AccountingRuleWithLinkedSettingDisplay
                    identifier="countCostBasisPnl"
                    :item="item.localData.countCostBasisPnl"
                  />
                </td>
                <td
                  :class="
                    diffClass(
                      item.localData.accountingTreatment,
                      item.remoteData.accountingTreatment
                    )
                  "
                >
                  <BadgeDisplay v-if="item.accountingTreatment">
                    {{ item.localData.accountingTreatment }}
                  </BadgeDisplay>
                  <span v-else>-</span>
                </td>
                <td class="align-bottom">
                  <RuiButtonGroup
                    v-model="resolution[item.localId]"
                    :disabled="!!solveAllUsing"
                    color="primary"
                    variant="outlined"
                    class="w-full rounded-b-0"
                    required
                  >
                    <template #default>
                      <RuiButton value="local" class="w-full">
                        {{ t('conflict_dialog.action.local') }}
                      </RuiButton>
                    </template>
                  </RuiButtonGroup>
                </td>
              </tr>
              <tr>
                <td
                  :class="
                    diffClass(
                      item.localData.taxable.value,
                      item.remoteData.taxable.value
                    )
                  "
                >
                  <AccountingRuleWithLinkedSettingDisplay
                    identifier="taxable"
                    :item="item.remoteData.taxable"
                  />
                </td>
                <td
                  :class="
                    diffClass(
                      item.localData.countEntireAmountSpend.value,
                      item.remoteData.countEntireAmountSpend.value
                    )
                  "
                >
                  <AccountingRuleWithLinkedSettingDisplay
                    identifier="countEntireAmountSpend"
                    :item="item.remoteData.countEntireAmountSpend"
                  />
                </td>
                <td
                  :class="
                    diffClass(
                      item.localData.countCostBasisPnl.value,
                      item.remoteData.countCostBasisPnl.value
                    )
                  "
                >
                  <AccountingRuleWithLinkedSettingDisplay
                    identifier="countCostBasisPnl"
                    :item="item.remoteData.countCostBasisPnl"
                  />
                </td>
                <td
                  :class="
                    diffClass(
                      item.localData.accountingTreatment,
                      item.remoteData.accountingTreatment
                    )
                  "
                >
                  <BadgeDisplay v-if="item.accountingTreatment">
                    {{ item.remoteData.accountingTreatment }}
                  </BadgeDisplay>
                  <span v-else>-</span>
                </td>
                <td class="align-top">
                  <RuiButtonGroup
                    v-model="resolution[item.localId]"
                    :disabled="!!solveAllUsing"
                    color="primary"
                    variant="outlined"
                    class="w-full rounded-t-0"
                    required
                  >
                    <template #default>
                      <RuiButton value="remote" class="w-full">
                        {{ t('conflict_dialog.action.remote') }}
                      </RuiButton>
                    </template>
                  </RuiButtonGroup>
                </td>
              </tr>
            </tbody>
          </template>
        </DataTable>
      </template>
    </CollectionHandler>
  </BigDialog>
</template>
