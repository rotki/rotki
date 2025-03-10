<script setup lang="ts">
import type { Trade, TradeEntry, TradeRequestPayload } from '@/types/history/trade';
import type { DataTableColumn } from '@rotki/ui-library';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import NavigatorLink from '@/components/helper/NavigatorLink.vue';
import RowActions from '@/components/helper/RowActions.vue';
import TableStatusFilter from '@/components/helper/TableStatusFilter.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import HistoryTableActions from '@/components/history/HistoryTableActions.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import IgnoredInAcountingIcon from '@/components/history/IgnoredInAcountingIcon.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import ExternalTradeFormDialog from '@/components/history/trades/ExternalTradeFormDialog.vue';
import TradeDetails from '@/components/history/trades/TradeDetails.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { type Filters, type Matcher, useTradeFilters } from '@/composables/filters/trades';
import { useIgnore } from '@/composables/history';
import { useHistoryAutoRefresh } from '@/composables/history/auto-refresh';
import { useTrades } from '@/composables/history/trades';
import { useCommonTableProps } from '@/composables/use-common-table-props';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { Routes } from '@/router/routes';
import { useConfirmStore } from '@/store/confirm';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { SavedFilterLocation } from '@/types/filtering';
import { IgnoreActionType } from '@/types/history/ignored';
import { Section } from '@/types/status';
import { createNewTrade } from '@/utils/history/trades';
import { toSnakeCase, type Writeable } from '@rotki/common';
import { omit } from 'es-toolkit';

const props = withDefaults(
  defineProps<{
    locationOverview?: string;
  }>(),
  {
    locationOverview: '',
  },
);

const { t } = useI18n();

const { locationOverview } = toRefs(props);

const hideIgnoredTrades = ref<boolean>(false);
const showIgnoredAssets = ref<boolean>(false);

const router = useRouter();
const route = useRoute();

const mainPage = computed(() => get(locationOverview) === '');

const tableHeaders = computed<DataTableColumn<TradeEntry>[]>(() => {
  const overview = !get(mainPage);
  const headers: DataTableColumn<TradeEntry>[] = [
    {
      cellClass: !overview ? '!p-0' : '!w-0 !max-w-[4rem]',
      class: !overview ? '!p-0' : '',
      key: 'ignoredInAccounting',
      label: '',
    },
    {
      align: 'center',
      cellClass: '!py-1',
      class: '!w-[7.5rem]',
      key: 'location',
      label: t('common.location'),
      sortable: true,
    },
    {
      align: overview ? 'start' : 'center',
      cellClass: '!px-0',
      class: '!px-0',
      key: 'type',
      label: t('closed_trades.headers.action'),
      sortable: true,
    },
    {
      align: 'end',
      key: 'amount',
      label: t('common.amount'),
      sortable: true,
    },
    {
      cellClass: '!py-1 !pl-0',
      class: '!pl-0',
      key: 'baseAsset',
      label: t('closed_trades.headers.base'),
    },
    {
      align: 'center',
      cellClass: '!px-0',
      class: '!px-0',
      key: 'description',
      label: '',
    },
    {
      align: 'end',
      key: 'quoteAmount',
      label: t('closed_trades.headers.quote_amount'),
    },
    {
      cellClass: '!py-1 !pl-0',
      class: '!pl-0',
      key: 'quoteAsset',
      label: t('closed_trades.headers.quote'),
    },
    {
      align: 'end',
      key: 'rate',
      label: t('closed_trades.headers.rate'),
      sortable: true,
    },
    {
      key: 'timestamp',
      label: t('common.datetime'),
      sortable: true,
    },
    {
      align: 'center',
      key: 'actions',
      label: t('common.actions_text'),
    },
  ];

  if (overview) {
    headers.splice(9, 1);
    headers.splice(1, 1);
  }

  return headers;
});

const extraParams = computed(() => ({
  excludeIgnoredAssets: !get(showIgnoredAssets),
  includeIgnoredTrades: !get(hideIgnoredTrades),
}));

const assetInfoRetrievalStore = useAssetInfoRetrieval();
const { assetSymbol } = assetInfoRetrievalStore;
const { deleteExternalTrade, fetchTrades, refreshTrades } = useTrades();
const { confirmationMessage, expanded, itemsToDelete: tradesToDelete, selected } = useCommonTableProps<TradeEntry>();

const editMode = ref<boolean>(false);
const modelValue = ref<Trade>();

const {
  fetchData,
  filters,
  isLoading,
  matchers,
  pagination,
  setPage,
  sort,
  state: trades,
} = usePaginationFilters<
  TradeEntry,
  TradeRequestPayload,
  Filters,
  Matcher
>(fetchTrades, {
  extraParams,
  filterSchema: useTradeFilters,
  history: get(mainPage) ? 'router' : false,
  locationOverview,
  onUpdateFilters(query) {
    set(hideIgnoredTrades, query.includeIgnoredTrades === 'false');
    set(showIgnoredAssets, query.excludeIgnoredAssets === 'false');
  },
  requestParams: computed<Partial<TradeRequestPayload>>(() => {
    const params: Writeable<Partial<TradeRequestPayload>> = {};
    const location = get(locationOverview);

    if (location)
      params.location = toSnakeCase(location);

    return params;
  }),
});

useHistoryAutoRefresh(fetchData);

function newExternalTrade() {
  set(modelValue, createNewTrade());
  set(editMode, false);
}

function editTradeHandler(trade: TradeEntry) {
  set(modelValue, omit(trade, ['ignoredInAccounting']));
  set(editMode, true);
}

const { floatingPrecision } = storeToRefs(useGeneralSettingsStore());

function promptForDelete(trade: TradeEntry) {
  const prep = (
    trade.tradeType === 'buy' ? t('closed_trades.description.with') : t('closed_trades.description.for')
  ).toLocaleLowerCase();

  const base = get(assetSymbol(trade.baseAsset));
  const quote = get(assetSymbol(trade.quoteAsset));
  set(
    confirmationMessage,
    t('closed_trades.confirmation.message', {
      action: trade.tradeType,
      amount: trade.amount.toFormat(get(floatingPrecision)),
      pair: `${base} ${prep} ${quote}`,
    }),
  );
  set(tradesToDelete, [trade]);
  showDeleteConfirmation();
}

function massDelete() {
  const selectedVal = get(selected);
  if (selectedVal.length === 1) {
    promptForDelete(selectedVal[0]);
    return;
  }

  set(tradesToDelete, [...selectedVal]);

  set(
    confirmationMessage,
    t('closed_trades.confirmation.multiple_message', {
      length: get(tradesToDelete).length,
    }),
  );

  showDeleteConfirmation();
}

async function deleteTradeHandler() {
  const tradesToDeleteVal = get(tradesToDelete);
  if (tradesToDeleteVal.length === 0)
    return;

  const ids = tradesToDeleteVal.map(trade => trade.tradeId);
  const { success } = await deleteExternalTrade(ids);

  if (!success)
    return;

  set(tradesToDelete, []);
  set(confirmationMessage, '');

  const selectedVal = [...get(selected)];
  set(
    selected,
    selectedVal.filter(trade => !ids.includes(trade.tradeId)),
  );

  await fetchData();
}

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.TRADES,
    toData: (item: TradeEntry) => item.tradeId,
  },
  selected,
  () => fetchData(),
);

const { show } = useConfirmStore();

function showDeleteConfirmation() {
  show(
    {
      message: get(confirmationMessage),
      title: t('closed_trades.confirmation.title'),
    },
    deleteTradeHandler,
  );
}

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.TRADES);

const value = computed({
  get: () => {
    if (!get(mainPage))
      return undefined;

    return get(selected).map(({ tradeId }: TradeEntry) => tradeId);
  },
  set: (values) => {
    set(
      selected,
      get(trades).data.filter(({ tradeId }: TradeEntry) => values?.includes(tradeId)),
    );
  },
});

function getItemClass(item: TradeEntry) {
  return item.ignoredInAccounting ? 'opacity-50' : '';
}

const pageRoute = Routes.HISTORY_TRADES;

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    newExternalTrade();
    await router.replace({ query: {} });
  }
  else {
    await fetchData();
    await refreshTrades();
  }
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});
</script>

<template>
  <TablePageLayout
    :hide-header="!!locationOverview"
    :child="!mainPage"
    :title="[t('navigation_menu.history'), t('closed_trades.title')]"
  >
    <template #buttons>
      <RuiTooltip>
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            @click="refreshTrades(true)"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('closed_trades.refresh_tooltip') }}
      </RuiTooltip>
      <RuiButton
        color="primary"
        data-cy="closed-trades__add-trade"
        @click="newExternalTrade()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('closed_trades.dialog.add.title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <template
        v-if="!!locationOverview"
        #header
      >
        <CardTitle>
          <NavigatorLink :to="pageRoute">
            {{ t('closed_trades.title') }}
          </NavigatorLink>
        </CardTitle>
      </template>

      <HistoryTableActions v-if="!locationOverview">
        <template #filter>
          <TableStatusFilter>
            <div class="py-1 max-w-[16rem]">
              <RuiSwitch
                v-model="hideIgnoredTrades"
                class="p-4"
                color="primary"
                hide-details
                :label="t('closed_trades.hide_ignored_trades')"
              />
              <RuiDivider />
              <RuiSwitch
                v-model="showIgnoredAssets"
                class="p-4"
                color="primary"
                hide-details
                :label="t('transactions.filter.show_ignored_assets')"
              />
            </div>
          </TableStatusFilter>
          <TableFilter
            v-model:matches="filters"
            class="min-w-full sm:min-w-[26rem]"
            :matchers="matchers"
            :location="SavedFilterLocation.HISTORY_TRADES"
          />
        </template>

        <RuiButton
          variant="outlined"
          color="error"
          :disabled="selected.length === 0"
          @click="massDelete()"
        >
          <RuiIcon name="lu-trash-2" />
        </RuiButton>

        <IgnoreButtons
          :disabled="selected.length === 0 || loading"
          @ignore="ignore($event)"
        />
        <div
          v-if="selected.length > 0"
          class="flex flex-row items-center gap-2"
        >
          {{ t('closed_trades.selected', { count: selected.length }) }}
          <RuiButton
            variant="text"
            @click="selected = []"
          >
            {{ t('common.actions.clear_selection') }}
          </RuiButton>
        </div>
      </HistoryTableActions>

      <CollectionHandler
        :collection="trades"
        @set-page="setPage($event)"
      >
        <template #default="{ data, limit, total, showUpgradeRow }">
          <RuiDataTable
            v-model="value"
            v-model:expanded="expanded"
            v-model:sort.external="sort"
            v-model:pagination.external="pagination"
            :cols="tableHeaders"
            :rows="data"
            :loading="isLoading || loading"
            :loading-text="t('trade_history.loading')"
            data-cy="closed-trades"
            :item-class="getItemClass"
            row-attr="tradeId"
            outlined
            single-expand
            sticky-header
          >
            <template #item.ignoredInAccounting="{ row }">
              <IgnoredInAcountingIcon v-if="row.ignoredInAccounting" />
              <span v-else />
            </template>
            <template #item.location="{ row }">
              <LocationDisplay
                data-cy="trade-location"
                :identifier="row.location"
              />
            </template>
            <template #item.type="{ row }">
              <BadgeDisplay :color="row.tradeType.toLowerCase() === 'sell' ? 'red' : 'green'">
                {{ row.tradeType }}
              </BadgeDisplay>
            </template>
            <template #item.baseAsset="{ row }">
              <AssetDetails
                data-cy="trade-base"
                opens-details
                hide-name
                :asset="row.baseAsset"
              />
            </template>
            <template #item.quoteAsset="{ row }">
              <AssetDetails
                hide-name
                opens-details
                :asset="row.quoteAsset"
                data-cy="trade-quote"
              />
            </template>
            <template #item.description="{ row }">
              {{ row.tradeType === 'buy' ? t('closed_trades.description.with') : t('closed_trades.description.for') }}
            </template>
            <template #item.rate="{ row }">
              <AmountDisplay
                class="closed-trades__trade__rate"
                :value="row.rate"
              />
            </template>
            <template #item.amount="{ row }">
              <AmountDisplay
                class="closed-trades__trade__amount"
                :value="row.amount"
              />
            </template>
            <template #item.quoteAmount="{ row }">
              <AmountDisplay
                class="closed-trades__trade__quote_amount"
                :value="row.amount.multipliedBy(row.rate)"
              />
            </template>
            <template #item.timestamp="{ row }">
              <DateDisplay :timestamp="row.timestamp" />
            </template>
            <template #item.actions="{ row }">
              <RowActions
                v-if="row.location === 'external'"
                :disabled="loading"
                :edit-tooltip="t('closed_trades.edit_tooltip')"
                :delete-tooltip="t('closed_trades.delete_tooltip')"
                @edit-click="editTradeHandler(row)"
                @delete-click="promptForDelete(row)"
              />
            </template>
            <template #expanded-item="{ row }">
              <TradeDetails :item="row" />
            </template>
            <template
              v-if="showUpgradeRow"
              #body.prepend="{ colspan }"
            >
              <UpgradeRow
                :limit="limit"
                :total="total"
                :colspan="colspan"
                :label="t('closed_trades.label')"
              />
            </template>
          </RuiDataTable>
        </template>
      </CollectionHandler>
      <ExternalTradeFormDialog
        v-model="modelValue"
        :edit-mode="editMode"
        :loading="loading"
        @refresh="fetchData()"
      />
    </RuiCard>
  </TablePageLayout>
</template>
