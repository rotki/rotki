<template>
  <fragment>
    <card outlined-body>
      <v-btn
        absolute
        fab
        top
        right
        dark
        color="primary"
        class="closed-trades__add-trade"
        @click="newExternalTrade()"
      >
        <v-icon> mdi-plus</v-icon>
      </v-btn>
      <template #title>
        <refresh-button
          :loading="refreshing"
          :tooltip="$t('closed_trades.refresh_tooltip')"
          @refresh="fetch(true)"
        />
        {{ $t('closed_trades.title') }}
      </template>
      <template #actions>
        <v-row>
          <v-col cols="12" sm="6">
            <ignore-buttons
              :disabled="selected.length === 0 || loading || refreshing"
              @ignore="ignore"
            />
            <div v-if="selected.length > 0" class="mt-2 ms-1">
              {{ $t('closed_trades.selected', { count: selected.length }) }}
              <v-btn small text @click="selected = []">
                {{ $t('closed_trades.clear_selection') }}
              </v-btn>
            </div>
          </v-col>
          <v-col cols="12" sm="6">
            <div class="pb-sm-8">
              <table-filter
                :matchers="matchers"
                @update:matches="updateFilterHandler($event)"
              />
            </div>
          </v-col>
        </v-row>
      </template>
      <data-table
        v-model="selected"
        :expanded.sync="expanded"
        :headers="tableHeaders"
        :items="data"
        :loading="refreshing"
        :options="options"
        :server-items-length="itemLength"
        class="closed-trades"
        :single-select="false"
        show-select
        item-key="tradeId"
        show-expand
        single-expand
        @update:options="updatePaginationHandler($event)"
      >
        <template #item.ignoredInAccounting="{ item, isMobile }">
          <div v-if="item.ignoredInAccounting">
            <badge-display v-if="isMobile" color="grey">
              <v-icon small> mdi-eye-off </v-icon>
              <span class="ml-2">
                {{ $t('closed_trades.headers.ignored') }}
              </span>
            </badge-display>
            <v-tooltip v-else bottom>
              <template #activator="{ on }">
                <badge-display color="grey" v-on="on">
                  <v-icon small> mdi-eye-off </v-icon>
                </badge-display>
              </template>
              <span>
                {{ $t('closed_trades.headers.ignored') }}
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
            :color="item.tradeType.toLowerCase() === 'sell' ? 'red' : 'green'"
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
              ? $t('closed_trades.description.with')
              : $t('closed_trades.description.for')
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
        <template #item.time="{ item }">
          <date-display :timestamp="item.timestamp" />
        </template>
        <template #item.actions="{ item }">
          <row-actions
            v-if="item.location === 'external'"
            :disabled="refreshing"
            :edit-tooltip="$t('closed_trades.edit_tooltip')"
            :delete-tooltip="$t('closed_trades.delete_tooltip')"
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
            :label="$t('closed_trades.label')"
          />
        </template>
      </data-table>
    </card>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :primary-action="$t('closed_trades.dialog.save')"
      :action-disabled="loading || !valid"
      :loading="loading"
      @confirm="confirmSave()"
      @cancel="clearDialog()"
    >
      <external-trade-form
        ref="form"
        v-model="valid"
        :edit="editableItem"
        :save-data="saveData"
      />
    </big-dialog>
    <confirm-dialog
      :display="tradeToDelete !== null"
      :title="$t('closed_trades.confirmation.title')"
      confirm-type="warning"
      :message="confirmationMessage"
      @cancel="tradeToDelete = null"
      @confirm="deleteTradeHandler()"
    />
  </fragment>
</template>

<script lang="ts">
import { computed, defineComponent, Ref, ref } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import ExternalTradeForm from '@/components/ExternalTradeForm.vue';
import DataTable from '@/components/helper/DataTable.vue';
import Fragment from '@/components/helper/Fragment';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import {
  MatchedKeyword,
  SearchMatcher
} from '@/components/history/filtering/types';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import TradeDetails from '@/components/history/TradeDetails.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import {
  setupAssetInfoRetrieval,
  setupSupportedAssets
} from '@/composables/balances';
import { setupStatusChecking } from '@/composables/common';
import {
  getCollectionData,
  setupEntryLimit,
  setupIgnore
} from '@/composables/history';
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import {
  NewTrade,
  Trade,
  TradeLocation,
  TradeRequestPayload,
  TradeType
} from '@/services/history/types';
import { Section } from '@/store/const';
import { useHistory, useTrades } from '@/store/history';
import { IgnoreActionType, TradeEntry } from '@/store/history/types';
import { Collection } from '@/types/collection';
import { uniqueStrings } from '@/utils/data';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';

enum TradeFilterKeys {
  BASE = 'base',
  QUOTE = 'quote',
  ACTION = 'action',
  START = 'start',
  END = 'end',
  LOCATION = 'location'
}

enum TradeFilterValueKeys {
  BASE = 'baseAsset',
  QUOTE = 'quoteAsset',
  ACTION = 'tradeType',
  START = 'fromTimestamp',
  END = 'toTimestamp',
  LOCATION = 'location'
}

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof Trade)[];
  sortDesc: boolean[];
};

const tableHeaders: DataTableHeader[] = [
  {
    text: '',
    value: 'ignoredInAccounting',
    sortable: false,
    class: 'pa-0',
    cellClass: 'pa-0'
  },
  {
    text: i18n.t('closed_trades.headers.location').toString(),
    value: 'location',
    width: '120px',
    align: 'center'
  },
  {
    text: i18n.t('closed_trades.headers.action').toString(),
    value: 'type',
    class: 'text-no-wrap',
    align: 'center'
  },
  {
    text: i18n.t('closed_trades.headers.amount').toString(),
    value: 'amount',
    align: 'end'
  },
  {
    text: i18n.t('closed_trades.headers.base').toString(),
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
    text: i18n.t('closed_trades.headers.quote').toString(),
    value: 'quoteAsset',
    sortable: false
  },
  {
    text: i18n.t('closed_trades.headers.rate').toString(),
    value: 'rate',
    align: 'end'
  },
  {
    text: i18n.t('closed_trades.headers.timestamp').toString(),
    value: 'time'
  },
  {
    text: i18n.t('closed_trades.headers.actions').toString(),
    value: 'actions',
    align: 'center',
    sortable: false,
    width: '50'
  },
  { text: '', value: 'data-table-expand', sortable: false }
];

export default defineComponent({
  name: 'ClosedTrades',
  components: {
    BadgeDisplay,
    RowActions,
    TradeDetails,
    TableFilter,
    DataTable,
    Fragment,
    IgnoreButtons,
    RefreshButton,
    UpgradeRow,
    DateDisplay,
    LocationDisplay,
    ExternalTradeForm,
    ConfirmDialog,
    BigDialog
  },
  emits: ['fetch', 'update:payload'],
  setup(_, { emit }) {
    const fetch = (refresh: boolean = false) => emit('fetch', refresh);

    const historyStore = useHistory();
    const tradeStore = useTrades();

    const { associatedLocations } = storeToRefs(historyStore);
    const { trades } = storeToRefs(tradeStore);

    const {
      addExternalTrade,
      editExternalTrade,
      deleteExternalTrade,
      updateTradesPayload
    } = tradeStore;

    const { data, limit, found, total } = getCollectionData<TradeEntry>(
      trades as Ref<Collection<TradeEntry>>
    );

    const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total);

    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const dialogTitle: Ref<string> = ref('');
    const dialogSubtitle: Ref<string> = ref('');
    const openDialog: Ref<boolean> = ref(false);
    const editableItem: Ref<TradeEntry | null> = ref(null);
    const tradeToDelete: Ref<TradeEntry | null> = ref(null);
    const confirmationMessage: Ref<string> = ref('');
    const expanded: Ref<TradeEntry[]> = ref([]);
    const valid: Ref<boolean> = ref(false);
    const form = ref<ExternalTradeForm | null>(null);

    const newExternalTrade = () => {
      dialogTitle.value = i18n.t('closed_trades.dialog.add.title').toString();
      dialogSubtitle.value = '';
      openDialog.value = true;
    };

    const editTradeHandler = (trade: TradeEntry) => {
      editableItem.value = trade;
      dialogTitle.value = i18n.t('closed_trades.dialog.edit.title').toString();
      dialogSubtitle.value = i18n
        .t('closed_trades.dialog.edit.subtitle')
        .toString();
      openDialog.value = true;
    };

    const { getAssetSymbol, getAssetIdentifierForSymbol } =
      setupAssetInfoRetrieval();

    const promptForDelete = (trade: TradeEntry) => {
      const prep = (
        trade.tradeType === 'buy'
          ? i18n.t('closed_trades.description.with').toString()
          : i18n.t('closed_trades.description.for').toString()
      ).toLocaleLowerCase();

      confirmationMessage.value = i18n
        .t('closed_trades.confirmation.message', {
          pair: `${getAssetSymbol(trade.baseAsset)} ${prep} ${getAssetSymbol(
            trade.quoteAsset
          )}`,
          action: trade.tradeType,
          amount: trade.amount
        })
        .toString();
      tradeToDelete.value = trade;
    };

    const deleteTradeHandler = async () => {
      if (!tradeToDelete.value) {
        return;
      }

      const { success } = await deleteExternalTrade(
        tradeToDelete.value?.tradeId
      );

      if (!success) {
        return;
      }

      tradeToDelete.value = null;
      confirmationMessage.value = '';
    };

    const clearDialog = () => {
      form.value?.reset();

      openDialog.value = false;
      editableItem.value = null;
    };

    const confirmSave = async () => {
      if (form.value) {
        const success = await form.value?.save();
        if (success) {
          clearDialog();
        }
      }
    };

    const saveData = async (trade: NewTrade | TradeEntry) => {
      if ((<TradeEntry>trade).tradeId) {
        return await editExternalTrade(trade as TradeEntry);
      }
      return await addExternalTrade(trade as NewTrade);
    };

    const { dateInputFormat } = setupSettings();

    const options: Ref<PaginationOptions | null> = ref(null);
    const filters: Ref<MatchedKeyword<TradeFilterValueKeys>> = ref({});

    const { supportedAssets } = setupSupportedAssets();
    const availableAssets = computed<string[]>(() => {
      return supportedAssets.value
        .map(value => getAssetSymbol(value.identifier))
        .filter(uniqueStrings);
    });

    const availableLocations = computed<TradeLocation[]>(() => {
      return associatedLocations.value;
    });

    const matchers = computed<
      SearchMatcher<TradeFilterKeys, TradeFilterValueKeys>[]
    >(() => [
      {
        key: TradeFilterKeys.BASE,
        keyValue: TradeFilterValueKeys.BASE,
        description: i18n.t('closed_trades.filter.base_asset').toString(),
        suggestions: () => availableAssets.value,
        validate: (asset: string) => availableAssets.value.includes(asset),
        transformer: (asset: string) => getAssetIdentifierForSymbol(asset) ?? ''
      },
      {
        key: TradeFilterKeys.QUOTE,
        keyValue: TradeFilterValueKeys.QUOTE,
        description: i18n.t('closed_trades.filter.quote_asset').toString(),
        suggestions: () => availableAssets.value,
        validate: (asset: string) => availableAssets.value.includes(asset),
        transformer: (asset: string) => getAssetIdentifierForSymbol(asset) ?? ''
      },
      {
        key: TradeFilterKeys.ACTION,
        keyValue: TradeFilterValueKeys.ACTION,
        description: i18n.t('closed_trades.filter.trade_type').toString(),
        suggestions: () => TradeType.options,
        validate: type => (TradeType.options as string[]).includes(type)
      },
      {
        key: TradeFilterKeys.START,
        keyValue: TradeFilterValueKeys.START,
        description: i18n.t('closed_trades.filter.start_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('closed_trades.filter.date_hint', {
            format: getDateInputISOFormat(dateInputFormat.value)
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, dateInputFormat.value))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, dateInputFormat.value).toString()
      },
      {
        key: TradeFilterKeys.END,
        keyValue: TradeFilterValueKeys.END,
        description: i18n.t('closed_trades.filter.end_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('closed_trades.filter.date_hint', {
            format: getDateInputISOFormat(dateInputFormat.value)
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, dateInputFormat.value))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, dateInputFormat.value).toString()
      },
      {
        key: TradeFilterKeys.LOCATION,
        keyValue: TradeFilterValueKeys.LOCATION,
        description: i18n.t('closed_trades.filter.location').toString(),
        suggestions: () => availableLocations.value,
        validate: location => availableLocations.value.includes(location as any)
      }
    ]);

    const updatePayloadHandler = () => {
      let paginationOptions = {};
      if (options.value) {
        options.value = {
          ...options.value,
          sortBy:
            options.value.sortBy.length > 0 ? [options.value.sortBy[0]] : [],
          sortDesc:
            options.value.sortDesc.length > 0 ? [options.value.sortDesc[0]] : []
        };

        const { itemsPerPage, page, sortBy, sortDesc } = options.value;
        const offset = (page - 1) * itemsPerPage;

        paginationOptions = {
          limit: itemsPerPage,
          offset,
          orderByAttribute: sortBy.length > 0 ? sortBy[0] : 'time',
          ascending: !sortDesc[0]
        };
      }

      const payload: Partial<TradeRequestPayload> = {
        ...filters.value,
        ...paginationOptions
      };

      updateTradesPayload(payload);
    };

    const updatePaginationHandler = (newOptions: PaginationOptions | null) => {
      options.value = newOptions;
      updatePayloadHandler();
    };

    const updateFilterHandler = (
      newFilters: MatchedKeyword<TradeFilterKeys>
    ) => {
      filters.value = newFilters;

      let newOptions = null;
      if (options.value) {
        newOptions = {
          ...options.value,
          page: 1
        };
      }

      updatePaginationHandler(newOptions);
    };

    const getId = (item: TradeEntry) => item.tradeId;
    const selected: Ref<TradeEntry[]> = ref([]);

    return {
      selected,
      tableHeaders,
      data,
      limit,
      found,
      total,
      itemLength,
      fetch,
      showUpgradeRow,
      loading: shouldShowLoadingScreen(Section.TRADES),
      refreshing: isSectionRefreshing(Section.TRADES),
      dialogTitle,
      dialogSubtitle,
      openDialog,
      editableItem,
      tradeToDelete,
      confirmationMessage,
      expanded,
      valid,
      newExternalTrade,
      editTradeHandler,
      promptForDelete,
      deleteTradeHandler,
      form,
      clearDialog,
      confirmSave,
      saveData,
      options,
      matchers,
      updatePaginationHandler,
      updateFilterHandler,
      ...setupIgnore(IgnoreActionType.TRADES, selected, data, fetch, getId)
    };
  }
});
</script>
