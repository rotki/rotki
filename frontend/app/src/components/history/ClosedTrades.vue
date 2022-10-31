<template>
  <fragment>
    <card outlined-body>
      <v-btn
        v-if="!locationOverview"
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
          v-if="!locationOverview"
          :loading="loading"
          :tooltip="tc('closed_trades.refresh_tooltip')"
          @refresh="fetch(true)"
        />
        <navigator-link :to="{ path: pageRoute }" :enabled="!!locationOverview">
          {{ tc('closed_trades.title') }}
        </navigator-link>
      </template>
      <template #actions>
        <v-row v-if="!locationOverview">
          <v-col cols="12" md="6">
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
                  <v-icon> mdi-delete-outline </v-icon>
                </v-btn>
              </v-col>
            </v-row>
            <div v-if="selected.length > 0" class="mt-2 ms-1">
              {{ tc('closed_trades.selected', 0, { count: selected.length }) }}
              <v-btn small text @click="selected = []">
                {{ tc('common.actions.clear_selection') }}
              </v-btn>
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="pb-md-8">
              <table-filter
                :matchers="matchers"
                @update:matches="updateFilter($event)"
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
        :loading="loading"
        :options="options"
        :server-items-length="itemLength"
        class="closed-trades"
        :single-select="false"
        :show-select="!locationOverview"
        :item-class="getClass"
        item-key="tradeId"
        show-expand
        single-expand
        multi-sort
        :must-sort="false"
        @update:options="updatePaginationHandler($event)"
      >
        <template #item.ignoredInAccounting="{ item, isMobile }">
          <div v-if="item.ignoredInAccounting">
            <badge-display v-if="isMobile" color="grey">
              <v-icon small> mdi-eye-off </v-icon>
              <span class="ml-2">
                {{ tc('common.ignored_in_accounting') }}
              </span>
            </badge-display>
            <v-tooltip v-else bottom>
              <template #activator="{ on }">
                <badge-display color="grey" v-on="on">
                  <v-icon small> mdi-eye-off </v-icon>
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
    </card>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :primary-action="tc('common.actions.save')"
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
      :display="tradesToDelete.length > 0"
      :title="tc('closed_trades.confirmation.title')"
      confirm-type="warning"
      :message="confirmationMessage"
      @cancel="tradesToDelete = []"
      @confirm="deleteTradeHandler()"
    />
  </fragment>
</template>

<script setup lang="ts">
import { dropRight } from 'lodash';
import { PropType, Ref } from 'vue';
import { DataTableHeader } from 'vuetify';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import Fragment from '@/components/helper/Fragment';
import NavigatorLink from '@/components/helper/NavigatorLink.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import ExternalTradeForm from '@/components/history/ExternalTradeForm.vue';
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import TradeDetails from '@/components/history/TradeDetails.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { isSectionLoading } from '@/composables/common';
import { useTradeFilters } from '@/composables/filters/trades';
import { setupIgnore } from '@/composables/history';
import { useRoute, useRouter } from '@/composables/router';
import { Routes } from '@/router/routes';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useTrades } from '@/store/history/trades';
import { IgnoreActionType, TradeEntry } from '@/store/history/types';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Collection } from '@/types/collection';
import { TradeLocation } from '@/types/history/trade-location';
import { NewTrade, Trade, TradeRequestPayload } from '@/types/history/trades';
import { Section } from '@/types/status';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof Trade)[];
  sortDesc: boolean[];
};

const props = defineProps({
  locationOverview: {
    required: false,
    type: String as PropType<TradeLocation | ''>,
    default: ''
  }
});

const emit = defineEmits(['fetch']);

const { locationOverview } = toRefs(props);

const selected: Ref<TradeEntry[]> = ref([]);
const options: Ref<PaginationOptions | null> = ref(null);
const dialogTitle: Ref<string> = ref('');
const dialogSubtitle: Ref<string> = ref('');
const openDialog: Ref<boolean> = ref(false);
const editableItem: Ref<TradeEntry | null> = ref(null);
const tradesToDelete: Ref<TradeEntry[]> = ref([]);
const confirmationMessage: Ref<string> = ref('');
const expanded: Ref<TradeEntry[]> = ref([]);
const valid: Ref<boolean> = ref(false);
const form: Ref<InstanceType<typeof ExternalTradeForm> | null> = ref(null);

const pageRoute = Routes.HISTORY_TRADES;

const { filters, matchers, updateFilter } = useTradeFilters();
const router = useRouter();
const route = useRoute();
const { tc } = useI18n();

const loading = isSectionLoading(Section.TRADES);

const tableHeaders = computed<DataTableHeader[]>(() => {
  let overview = get(locationOverview);
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

const tradeStore = useTrades();
const assetInfoRetrievalStore = useAssetInfoRetrieval();
const { assetSymbol } = assetInfoRetrievalStore;
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

const newExternalTrade = () => {
  set(dialogTitle, tc('closed_trades.dialog.add.title'));
  set(dialogSubtitle, '');
  set(openDialog, true);
};

const editTradeHandler = (trade: TradeEntry) => {
  set(editableItem, trade);
  set(dialogTitle, tc('closed_trades.dialog.edit.title'));
  set(dialogSubtitle, tc('closed_trades.dialog.edit.subtitle'));
  set(openDialog, true);
};

const { floatingPrecision } = storeToRefs(useGeneralSettingsStore());

const promptForDelete = (trade: TradeEntry) => {
  const prep = (
    trade.tradeType === 'buy'
      ? tc('closed_trades.description.with')
      : tc('closed_trades.description.for')
  ).toLocaleLowerCase();

  let base = get(assetSymbol(trade.baseAsset));
  let quote = get(assetSymbol(trade.quoteAsset));
  set(
    confirmationMessage,
    tc('closed_trades.confirmation.message', 0, {
      pair: `${base} ${prep} ${quote}`,
      action: trade.tradeType,
      amount: trade.amount.toFormat(get(floatingPrecision))
    })
  );
  set(tradesToDelete, [trade]);
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
};

const clearDialog = () => {
  get(form)?.reset();

  set(openDialog, false);
  set(editableItem, null);
};

const confirmSave = async () => {
  if (get(form)) {
    const success = await get(form)?.save();
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

const updatePayloadHandler = async () => {
  let paginationOptions = {};

  const optionsVal = get(options);
  if (optionsVal) {
    const { itemsPerPage, page, sortBy, sortDesc } = optionsVal;
    const offset = (page - 1) * itemsPerPage;

    paginationOptions = {
      limit: itemsPerPage,
      offset,
      orderByAttributes: sortBy.length > 0 ? sortBy : ['timestamp'],
      ascending:
        sortDesc.length > 1 ? dropRight(sortDesc).map(bool => !bool) : [false]
    };
  }

  if (get(locationOverview)) {
    filters.value.location = get(locationOverview) as TradeLocation;
  }

  const payload: Partial<TradeRequestPayload> = {
    ...(get(filters) as Partial<TradeRequestPayload>),
    ...paginationOptions
  };

  await updateTradesPayload(payload);
};

const updatePaginationHandler = async (
  newOptions: PaginationOptions | null
) => {
  set(options, newOptions);
  await updatePayloadHandler();
};

const getClass = (item: TradeEntry) => {
  return item.ignoredInAccounting ? 'darken-row' : '';
};

watch(filters, async (filters, oldValue) => {
  if (filters === oldValue) {
    return;
  }
  let newOptions = null;
  if (get(options)) {
    newOptions = {
      ...get(options)!,
      page: 1
    };
  }

  await updatePaginationHandler(newOptions);
});

const fetch = (refresh: boolean = false) => emit('fetch', refresh);

const { ignore } = setupIgnore(
  IgnoreActionType.TRADES,
  selected,
  fetch,
  (item: TradeEntry) => item.tradeId
);

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    newExternalTrade();
    await router.replace({ query: {} });
  }
});
</script>
