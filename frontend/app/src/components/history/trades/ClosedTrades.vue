<script setup lang="ts">
import { Routes } from '@/router/routes';
import { Section } from '@/types/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { SavedFilterLocation } from '@/types/filtering';
import type { Writeable } from '@/types';
import type {
  Trade,
  TradeEntry,
  TradeRequestPayload,
} from '@/types/history/trade';
import type { Collection } from '@/types/collection';
import type { Filters, Matcher } from '@/composables/filters/trades';
import type { DataTableColumn } from '@rotki/ui-library-compat';

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

const hideIgnoredTrades: Ref<boolean> = ref(false);
const showIgnoredAssets: Ref<boolean> = ref(false);

const router = useRouter();
const route = useRoute();

const mainPage = computed(() => get(locationOverview) === '');

const tableHeaders = computed<DataTableColumn[]>(() => {
  const overview = !get(mainPage);
  const headers: DataTableColumn[] = [
    {
      label: '',
      key: 'ignoredInAccounting',
      class: !overview ? '!p-0' : '',
      cellClass: !overview ? '!p-0' : '!w-0 !max-w-[4rem]',
    },
    {
      label: t('common.location'),
      key: 'location',
      class: '!w-[7.5rem]',
      cellClass: '!py-1',
      align: 'center',
      sortable: true,
    },
    {
      label: t('closed_trades.headers.action'),
      key: 'type',
      align: overview ? 'start' : 'center',
      class: `text-no-wrap${overview ? ' !pl-0' : ''}`,
      cellClass: overview ? '!pl-0' : 'py-1',
      sortable: true,
    },
    {
      label: t('common.amount'),
      key: 'amount',
      align: 'end',
      sortable: true,
    },
    {
      label: t('closed_trades.headers.base'),
      key: 'baseAsset',
      cellClass: '!py-1',
    },
    {
      label: '',
      key: 'description',
    },
    {
      label: t('closed_trades.headers.quote'),
      key: 'quoteAsset',
      cellClass: '!py-1',
    },
    {
      label: t('closed_trades.headers.rate'),
      key: 'rate',
      align: 'end',
      sortable: true,
    },
    {
      label: t('common.datetime'),
      key: 'timestamp',
      sortable: true,
    },
    {
      label: t('common.actions_text'),
      key: 'actions',
      align: 'center',
      class: '!w-px',
    },
  ];

  if (overview) {
    headers.splice(9, 1);
    headers.splice(1, 1);
  }

  return headers;
});

const extraParams = computed(() => ({
  includeIgnoredTrades: !get(hideIgnoredTrades),
  excludeIgnoredAssets: !get(showIgnoredAssets),
}));

const assetInfoRetrievalStore = useAssetInfoRetrieval();
const { assetSymbol } = assetInfoRetrievalStore;

const { deleteExternalTrade, fetchTrades, refreshTrades } = useTrades();

const {
  selected,
  editableItem,
  itemsToDelete: tradesToDelete,
  confirmationMessage,
  expanded,
  isLoading,
  state: trades,
  filters,
  matchers,
  setPage,
  pagination,
  sort,
  setFilter,
  fetchData,
} = usePaginationFilters<
  Trade,
  TradeRequestPayload,
  TradeEntry,
  Collection<TradeEntry>,
  Filters,
  Matcher
>(locationOverview, mainPage, useTradeFilters, fetchTrades, {
  onUpdateFilters(query) {
    set(hideIgnoredTrades, query.includeIgnoredTrades === 'false');
    set(showIgnoredAssets, query.excludeIgnoredAssets === 'false');
  },
  customPageParams: computed<Partial<TradeRequestPayload>>(() => {
    const params: Writeable<Partial<TradeRequestPayload>> = {};
    const location = get(locationOverview);

    if (location)
      params.location = toSnakeCase(location);

    return params;
  }),
  extraParams,
});

useHistoryAutoRefresh(fetchData);

const { setOpenDialog, setPostSubmitFunc } = useTradesForm();

setPostSubmitFunc(fetchData);

function newExternalTrade() {
  set(editableItem, null);
  setOpenDialog(true);
}

function editTradeHandler(trade: TradeEntry) {
  set(editableItem, trade);
  setOpenDialog(true);
}

const { floatingPrecision } = storeToRefs(useGeneralSettingsStore());

function promptForDelete(trade: TradeEntry) {
  const prep = (
    trade.tradeType === 'buy'
      ? t('closed_trades.description.with')
      : t('closed_trades.description.for')
  ).toLocaleLowerCase();

  const base = get(assetSymbol(trade.baseAsset));
  const quote = get(assetSymbol(trade.quoteAsset));
  set(
    confirmationMessage,
    t('closed_trades.confirmation.message', {
      pair: `${base} ${prep} ${quote}`,
      action: trade.tradeType,
      amount: trade.amount.toFormat(get(floatingPrecision)),
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
      title: t('closed_trades.confirmation.title'),
      message: get(confirmationMessage),
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
    set(selected, get(trades).data.filter(({ tradeId }: TradeEntry) => values?.includes(tradeId)));
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
              <RuiIcon name="refresh-line" />
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
          <RuiIcon name="add-line" />
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
          <NavigatorLink :to="{ path: pageRoute }">
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
            class="min-w-full sm:min-w-[20rem]"
            :matches="filters"
            :matchers="matchers"
            :location="SavedFilterLocation.HISTORY_TRADES"
            @update:matches="setFilter($event)"
          />
        </template>

        <RuiButton
          variant="outlined"
          color="error"
          :disabled="selected.length === 0"
          @click="massDelete()"
        >
          <RuiIcon name="delete-bin-line" />
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
            :expanded.sync="expanded"
            :cols="tableHeaders"
            :rows="data"
            :loading="isLoading || loading"
            :loading-text="t('trade_history.loading')"
            :pagination.sync="pagination"
            :pagination-modifiers="{ external: true }"
            :sort.sync="sort"
            :sort-modifiers="{ external: true }"
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
              <BadgeDisplay
                :color="
                  row.tradeType.toLowerCase() === 'sell' ? 'red' : 'green'
                "
              >
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
              {{
                row.tradeType === 'buy'
                  ? t('closed_trades.description.with')
                  : t('closed_trades.description.for')
              }}
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
        :loading="loading"
        :editable-item="editableItem"
      />
    </RuiCard>
  </TablePageLayout>
</template>
