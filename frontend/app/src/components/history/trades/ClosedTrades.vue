<script setup lang="ts">
import { type Ref } from 'vue';
import { type DataTableHeader } from 'vuetify';
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

const { locationOverview, mainPage } = toRefs(props);

const hideIgnoredTrades: Ref<boolean> = ref(false);

const { tc } = useI18n();
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
      text: tc('common.location'),
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: tc('closed_trades.headers.action'),
      value: 'type',
      align: 'center',
      class: `text-no-wrap ${overview ? 'pl-0' : ''}`,
      cellClass: overview ? 'pl-0' : ''
    },
    {
      text: tc('common.amount'),
      value: 'amount',
      align: 'end'
    },
    {
      text: tc('closed_trades.headers.base'),
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
      text: tc('closed_trades.headers.quote'),
      value: 'quoteAsset',
      sortable: false
    },
    {
      text: tc('closed_trades.headers.rate'),
      value: 'rate',
      align: 'end'
    },
    {
      text: tc('common.datetime'),
      value: 'timestamp'
    },
    {
      text: tc('closed_trades.headers.actions'),
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

const assetInfoRetrievalStore = useAssetInfoRetrieval();
const { assetSymbol } = assetInfoRetrievalStore;

const { deleteExternalTrade, fetchTrades, refreshTrades } = useTrades();

const {
  options,
  selected,
  openDialog,
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
} = useHistoryPaginationFilter<Trade, TradeRequestPayload, TradeEntry>(
  locationOverview,
  mainPage,
  useTradeFilters,
  fetchTrades,
  { hideIgnoredTrades }
);

useHistoryAutoRefresh(fetchData);

const newExternalTrade = () => {
  set(editableItem, null);
  set(openDialog, true);
};

const editTradeHandler = (trade: TradeEntry) => {
  set(editableItem, trade);
  set(openDialog, true);
};

const { floatingPrecision } = storeToRefs(useGeneralSettingsStore());

const promptForDelete = (trade: TradeEntry) => {
  const prep = (
    trade.tradeType === 'buy'
      ? tc('closed_trades.description.with')
      : tc('closed_trades.description.for')
  ).toLocaleLowerCase();

  const base = get(assetSymbol(trade.baseAsset));
  const quote = get(assetSymbol(trade.quoteAsset));
  set(
    confirmationMessage,
    tc('closed_trades.confirmation.message', 0, {
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
    tc('closed_trades.confirmation.multiple_message', 0, {
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
      title: tc('closed_trades.confirmation.title'),
      message: get(confirmationMessage)
    },
    () => deleteTradeHandler()
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

watch(hideIgnoredTrades, () => {
  setPage(1);
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});
</script>

<template>
  <fragment>
    <card outlined-body class="mt-8">
      <v-btn
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
        <v-icon> mdi-plus</v-icon>
      </v-btn>
      <template #title>
        <refresh-button
          v-if="!locationOverview"
          :loading="loading"
          :tooltip="tc('closed_trades.refresh_tooltip')"
          @refresh="refreshTrades(true)"
        />
        <navigator-link :to="{ path: pageRoute }" :enabled="!!locationOverview">
          {{ tc('closed_trades.title') }}
        </navigator-link>
      </template>
      <template #actions>
        <v-row v-if="!locationOverview">
          <v-col cols="12" md="6" class="d-flex">
            <div>
              <v-row>
                <v-col cols="auto">
                  <ignore-buttons
                    :disabled="selected.length === 0 || loading"
                    @ignore="ignore"
                  />
                </v-col>
                <v-col>
                  <v-btn
                    text
                    outlined
                    color="red"
                    :disabled="selected.length === 0"
                    @click="massDelete"
                  >
                    <v-icon> mdi-delete-outline</v-icon>
                  </v-btn>
                </v-col>
              </v-row>
              <div v-if="selected.length > 0" class="mt-2 ms-1">
                {{
                  tc('closed_trades.selected', 0, { count: selected.length })
                }}
                <v-btn small text @click="selected = []">
                  {{ tc('common.actions.clear_selection') }}
                </v-btn>
              </div>
            </div>
            <div>
              <v-switch
                v-model="hideIgnoredTrades"
                class="mt-0 ml-8"
                hide-details
                :label="tc('closed_trades.hide_ignored_trades')"
              />
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="pb-md-8">
              <table-filter
                :matches="filters"
                :matchers="matchers"
                :location="SavedFilterLocation.HISTORY_TRADES"
                @update:matches="setFilter($event)"
              />
            </div>
          </v-col>
        </v-row>
      </template>

      <collection-handler :collection="trades" @set-page="setPage">
        <template #default="{ data, limit, total, showUpgradeRow, itemLength }">
          <data-table
            v-model="selected"
            :expanded.sync="expanded"
            :headers="tableHeaders"
            :items="data"
            :loading="isLoading"
            :loading-text="tc('trade_history.loading')"
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
                <badge-display v-if="isMobile" color="grey">
                  <v-icon small> mdi-eye-off</v-icon>
                  <span class="ml-2">
                    {{ tc('common.ignored_in_accounting') }}
                  </span>
                </badge-display>
                <v-tooltip v-else bottom>
                  <template #activator="{ on }">
                    <badge-display color="grey" v-on="on">
                      <v-icon small> mdi-eye-off</v-icon>
                    </badge-display>
                  </template>
                  <span>
                    {{ tc('common.ignored_in_accounting') }}
                  </span>
                </v-tooltip>
              </div>
            </template>
            <template #item.location="{ item }">
              <location-display
                data-cy="trade-location"
                :identifier="item.location"
              />
            </template>
            <template #item.type="{ item }">
              <badge-display
                :color="
                  item.tradeType.toLowerCase() === 'sell' ? 'red' : 'green'
                "
              >
                {{ item.tradeType }}
              </badge-display>
            </template>
            <template #item.baseAsset="{ item }">
              <asset-details
                data-cy="trade-base"
                opens-details
                hide-name
                :asset="item.baseAsset"
              />
            </template>
            <template #item.quoteAsset="{ item }">
              <asset-details
                hide-name
                opens-details
                :asset="item.quoteAsset"
                data-cy="trade-quote"
              />
            </template>
            <template #item.description="{ item }">
              {{
                item.tradeType === 'buy'
                  ? tc('closed_trades.description.with')
                  : tc('closed_trades.description.for')
              }}
            </template>
            <template #item.rate="{ item }">
              <amount-display
                class="closed-trades__trade__rate"
                :value="item.rate"
              />
            </template>
            <template #item.amount="{ item }">
              <amount-display
                class="closed-trades__trade__amount"
                :value="item.amount"
              />
            </template>
            <template #item.timestamp="{ item }">
              <date-display :timestamp="item.timestamp" />
            </template>
            <template #item.actions="{ item }">
              <row-actions
                v-if="item.location === 'external'"
                :disabled="loading"
                :edit-tooltip="tc('closed_trades.edit_tooltip')"
                :delete-tooltip="tc('closed_trades.delete_tooltip')"
                @edit-click="editTradeHandler(item)"
                @delete-click="promptForDelete(item)"
              />
            </template>
            <template #expanded-item="{ headers, item }">
              <trade-details :span="headers.length" :item="item" />
            </template>
            <template v-if="showUpgradeRow" #body.prepend="{ headers }">
              <upgrade-row
                :limit="limit"
                :total="total"
                :colspan="headers.length"
                :label="tc('closed_trades.label')"
              />
            </template>
          </data-table>
        </template>
      </collection-handler>
    </card>
    <external-trade-form-dialog
      v-model="openDialog"
      :loading="loading"
      :editable-item="editableItem"
      :open="openDialog"
      @reset-edit="editableItem = null"
      @saved="fetchData()"
    />
  </fragment>
</template>
