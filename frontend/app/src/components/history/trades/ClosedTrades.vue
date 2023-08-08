<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import { type Collection } from '@/types/collection';
import Fragment from '@/components/helper/Fragment';
import { Routes } from '@/router/routes';
import { type TradeLocation } from '@/types/history/trade/location';
import {
  type Trade,
  type TradeEntry,
  type TradeRequestPayload
} from '@/types/history/trade';
import { Section } from '@/types/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { SavedFilterLocation } from '@/types/filtering';
import type { Filters, Matcher } from '@/composables/filters/trades';

const props = withDefaults(
  defineProps<{
    locationOverview?: TradeLocation;
    mainPage?: boolean;
  }>(),
  {
    locationOverview: '',
    mainPage: false
  }
);

const { t } = useI18n();

const { locationOverview, mainPage } = toRefs(props);

const hideIgnoredTrades: Ref<boolean> = ref(false);

const router = useRouter();
const route = useRoute();

const tableHeaders = computed<DataTableHeader[]>(() => {
  const overview = get(locationOverview);
  const headers: DataTableHeader[] = [
    {
      text: '',
      value: 'ignoredInAccounting',
      sortable: false,
      class: !overview ? 'pa-0' : 'pr-0',
      cellClass: !overview ? 'pa-0' : 'pr-0'
    },
    {
      text: t('common.location'),
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: t('closed_trades.headers.action'),
      value: 'type',
      align: overview ? 'start' : 'center',
      class: `text-no-wrap ${overview ? 'pl-0' : ''}`,
      cellClass: overview ? 'pl-0' : ''
    },
    {
      text: t('common.amount'),
      value: 'amount',
      align: 'end'
    },
    {
      text: t('closed_trades.headers.base'),
      value: 'baseAsset',
      sortable: false
    },
    {
      text: '',
      value: 'description',
      sortable: false,
      width: '40px'
    },
    {
      text: t('closed_trades.headers.quote'),
      value: 'quoteAsset',
      sortable: false
    },
    {
      text: t('closed_trades.headers.rate'),
      value: 'rate',
      align: 'end'
    },
    {
      text: t('common.datetime'),
      value: 'timestamp'
    },
    {
      text: t('closed_trades.headers.actions'),
      value: 'actions',
      align: 'center',
      sortable: false,
      width: '1px'
    },
    { text: '', value: 'data-table-expand', sortable: false }
  ];

  if (overview) {
    headers.splice(9, 1);
    headers.splice(1, 1);
  }

  return headers;
});

const extraParams = computed(() => ({
  includeIgnoredTrades: (!get(hideIgnoredTrades)).toString()
}));

watch(hideIgnoredTrades, () => {
  setPage(1);
});

const assetInfoRetrievalStore = useAssetInfoRetrieval();
const { assetSymbol } = assetInfoRetrievalStore;

const { deleteExternalTrade, fetchTrades, refreshTrades } = useTrades();

const {
  options,
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
  setOptions,
  setFilter,
  fetchData
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
  },
  extraParams
});

useHistoryAutoRefresh(fetchData);

const { setOpenDialog, setPostSubmitFunc } = useTradesForm();

setPostSubmitFunc(fetchData);

const newExternalTrade = () => {
  set(editableItem, null);
  setOpenDialog(true);
};

const editTradeHandler = (trade: TradeEntry) => {
  set(editableItem, trade);
  setOpenDialog(true);
};

const { floatingPrecision } = storeToRefs(useGeneralSettingsStore());

const promptForDelete = (trade: TradeEntry) => {
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
      amount: trade.amount.toFormat(get(floatingPrecision))
    })
  );
  set(tradesToDelete, [trade]);
  showDeleteConfirmation();
};

const massDelete = () => {
  const selectedVal = get(selected);
  if (selectedVal.length === 1) {
    promptForDelete(selectedVal[0]);
    return;
  }

  set(tradesToDelete, [...selectedVal]);

  set(
    confirmationMessage,
    t('closed_trades.confirmation.multiple_message', {
      length: get(tradesToDelete).length
    })
  );

  showDeleteConfirmation();
};

const deleteTradeHandler = async () => {
  const tradesToDeleteVal = get(tradesToDelete);
  if (tradesToDeleteVal.length === 0) {
    return;
  }

  const ids = tradesToDeleteVal.map(trade => trade.tradeId);
  const { success } = await deleteExternalTrade(ids);

  if (!success) {
    return;
  }

  set(tradesToDelete, []);
  set(confirmationMessage, '');

  const selectedVal = [...get(selected)];
  set(
    selected,
    selectedVal.filter(trade => !ids.includes(trade.tradeId))
  );

  await fetchData();
};

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.TRADES,
    toData: (item: TradeEntry) => item.tradeId
  },
  selected,
  () => fetchData()
);

const { show } = useConfirmStore();

const showDeleteConfirmation = () => {
  show(
    {
      title: t('closed_trades.confirmation.title'),
      message: get(confirmationMessage)
    },
    deleteTradeHandler
  );
};

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.TRADES);

const getItemClass = (item: TradeEntry) =>
  item.ignoredInAccounting ? 'darken-row' : '';

const pageRoute = Routes.HISTORY_TRADES;

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    newExternalTrade();
    await router.replace({ query: {} });
  } else {
    await fetchData();
    await refreshTrades();
  }
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});
</script>

<template>
  <Fragment>
    <Card outlined-body class="mt-8">
      <VBtn
        v-if="!locationOverview"
        absolute
        fab
        top
        right
        dark
        color="primary"
        data-cy="closed-trades__add-trade"
        @click="newExternalTrade()"
      >
        <VIcon> mdi-plus </VIcon>
      </VBtn>
      <template #title>
        <RefreshButton
          v-if="!locationOverview"
          :loading="loading"
          :tooltip="t('closed_trades.refresh_tooltip')"
          @refresh="refreshTrades(true)"
        />
        <NavigatorLink :to="{ path: pageRoute }" :enabled="!!locationOverview">
          {{ t('closed_trades.title') }}
        </NavigatorLink>
      </template>
      <template v-if="!locationOverview" #actions>
        <VRow>
          <VCol cols="12" md="6" class="d-flex">
            <div>
              <VRow>
                <VCol cols="auto">
                  <IgnoreButtons
                    :disabled="selected.length === 0 || loading"
                    @ignore="ignore($event)"
                  />
                </VCol>
                <VCol>
                  <VBtn
                    text
                    outlined
                    color="red"
                    :disabled="selected.length === 0"
                    @click="massDelete()"
                  >
                    <VIcon> mdi-delete-outline </VIcon>
                  </VBtn>
                </VCol>
              </VRow>
              <div v-if="selected.length > 0" class="mt-2 ms-1">
                {{ t('closed_trades.selected', { count: selected.length }) }}
                <VBtn small text @click="selected = []">
                  {{ t('common.actions.clear_selection') }}
                </VBtn>
              </div>
            </div>
            <div>
              <VSwitch
                v-model="hideIgnoredTrades"
                class="mt-0 ml-8"
                hide-details
                :label="t('closed_trades.hide_ignored_trades')"
              />
            </div>
          </VCol>
          <VCol cols="12" md="6">
            <div class="pb-md-8">
              <TableFilter
                :matches="filters"
                :matchers="matchers"
                :location="SavedFilterLocation.HISTORY_TRADES"
                @update:matches="setFilter($event)"
              />
            </div>
          </VCol>
        </VRow>
      </template>

      <CollectionHandler :collection="trades" @set-page="setPage($event)">
        <template #default="{ data, limit, total, showUpgradeRow, itemLength }">
          <DataTable
            v-model="selected"
            :expanded.sync="expanded"
            :headers="tableHeaders"
            :items="data"
            :loading="isLoading"
            :loading-text="t('trade_history.loading')"
            :options="options"
            :server-items-length="itemLength"
            data-cy="closed-trades"
            :single-select="false"
            :show-select="!locationOverview"
            :item-class="getItemClass"
            item-key="tradeId"
            show-expand
            single-expand
            multi-sort
            :must-sort="false"
            @update:options="setOptions($event)"
          >
            <template #item.ignoredInAccounting="{ item, isMobile }">
              <div v-if="item.ignoredInAccounting">
                <BadgeDisplay v-if="isMobile" color="grey">
                  <VIcon small> mdi-eye-off</VIcon>
                  <span class="ml-2">
                    {{ t('common.ignored_in_accounting') }}
                  </span>
                </BadgeDisplay>
                <VTooltip v-else bottom>
                  <template #activator="{ on }">
                    <BadgeDisplay color="grey" v-on="on">
                      <VIcon small> mdi-eye-off</VIcon>
                    </BadgeDisplay>
                  </template>
                  <span>
                    {{ t('common.ignored_in_accounting') }}
                  </span>
                </VTooltip>
              </div>
            </template>
            <template #item.location="{ item }">
              <LocationDisplay
                data-cy="trade-location"
                :identifier="item.location"
              />
            </template>
            <template #item.type="{ item }">
              <BadgeDisplay
                :color="
                  item.tradeType.toLowerCase() === 'sell' ? 'red' : 'green'
                "
              >
                {{ item.tradeType }}
              </BadgeDisplay>
            </template>
            <template #item.baseAsset="{ item }">
              <AssetDetails
                data-cy="trade-base"
                opens-details
                hide-name
                :asset="item.baseAsset"
              />
            </template>
            <template #item.quoteAsset="{ item }">
              <AssetDetails
                hide-name
                opens-details
                :asset="item.quoteAsset"
                data-cy="trade-quote"
              />
            </template>
            <template #item.description="{ item }">
              {{
                item.tradeType === 'buy'
                  ? t('closed_trades.description.with')
                  : t('closed_trades.description.for')
              }}
            </template>
            <template #item.rate="{ item }">
              <AmountDisplay
                class="closed-trades__trade__rate"
                :value="item.rate"
              />
            </template>
            <template #item.amount="{ item }">
              <AmountDisplay
                class="closed-trades__trade__amount"
                :value="item.amount"
              />
            </template>
            <template #item.timestamp="{ item }">
              <DateDisplay :timestamp="item.timestamp" />
            </template>
            <template #item.actions="{ item }">
              <RowActions
                v-if="item.location === 'external'"
                :disabled="loading"
                :edit-tooltip="t('closed_trades.edit_tooltip')"
                :delete-tooltip="t('closed_trades.delete_tooltip')"
                @edit-click="editTradeHandler(item)"
                @delete-click="promptForDelete(item)"
              />
            </template>
            <template #expanded-item="{ headers, item }">
              <TradeDetails :span="headers.length" :item="item" />
            </template>
            <template v-if="showUpgradeRow" #body.prepend="{ headers }">
              <UpgradeRow
                :limit="limit"
                :total="total"
                :colspan="headers.length"
                :label="t('closed_trades.label')"
              />
            </template>
          </DataTable>
        </template>
      </CollectionHandler>
    </Card>
    <ExternalTradeFormDialog :loading="loading" :editable-item="editableItem" />
  </Fragment>
</template>
