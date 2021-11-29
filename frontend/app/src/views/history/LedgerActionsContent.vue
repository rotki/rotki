<template>
  <card outlined-body>
    <v-btn
      absolute
      fab
      top
      right
      dark
      color="primary"
      class="ledger-actions__add"
      @click="$emit('show-form')"
    >
      <v-icon> mdi-plus </v-icon>
    </v-btn>
    <template #title>
      <refresh-button
        :loading="refreshing"
        :tooltip="$t('ledger_actions.refresh_tooltip')"
        @refresh="$emit('refresh')"
      />
      {{ $t('ledger_actions.title') }}
    </template>
    <template #actions>
      <v-row>
        <v-col cols="12" sm="6">
          <ignore-buttons
            :disabled="selected.length === 0 || loading || refreshing"
            @ignore="ignore"
          />
        </v-col>
        <v-col cols="12" sm="6">
          <table-filter
            :matchers="matchers"
            @update:matches="updateFilter($event)"
          />
        </v-col>
      </v-row>
    </template>
    <data-table
      :headers="tableHeaders"
      :items="visibleItems"
      show-expand
      single-expand
      :expanded="expanded"
      sort-by="timestamp"
      item-key="identifier"
      :page.sync="page"
      :loading="refreshing"
    >
      <template #header.selection>
        <v-simple-checkbox
          :ripple="false"
          :value="allSelected"
          color="primary"
          @input="setSelected($event)"
        />
      </template>
      <template #item.selection="{ item }">
        <v-simple-checkbox
          :ripple="false"
          color="primary"
          :value="selected.includes(item.identifier)"
          @input="selectionChanged(item.identifier, $event)"
        />
      </template>
      <template #item.actionType="{ item }">
        <event-type-display :event-type="item.actionType" />
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
      <template #item.location="{ item }">
        <location-display :identifier="item.location" />
      </template>
      <template #item.asset="{ item }">
        <asset-details opens-details :asset="item.asset" />
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.ignoredInAccounting="{ item }">
        <v-icon v-if="item.ignoredInAccounting">mdi-check</v-icon>
      </template>
      <template #item.actions="{ item }">
        <row-actions
          :disabled="refreshing"
          :edit-tooltip="$t('ledger_actions.edit_tooltip')"
          :delete-tooltip="$t('ledger_actions.delete_tooltip')"
          @edit-click="$emit('show-form', item)"
          @delete-click="$emit('delete-action', item.identifier)"
        />
      </template>
      <template v-if="showUpgradeRow" #body.prepend="{ headers }">
        <upgrade-row
          :total="total"
          :limit="limit"
          :colspan="headers.length"
          :label="$t('ledger_actions.label')"
        />
      </template>
      <template #expanded-item="{ headers, item }">
        <ledger-action-details :span="headers.length" :item="item" />
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  Ref,
  ref,
  toRefs,
  UnwrapRef,
  watch
} from '@vue/composition-api';
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import * as logger from 'loglevel';
import { DataTableHeader } from 'vuetify';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import {
  MatchedKeyword,
  SearchMatcher
} from '@/components/history/filtering/types';
import {
  checkIfMatch,
  endMatch,
  startMatch
} from '@/components/history/filtering/utils';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import { AssetSymbolGetter } from '@/store/balances/types';
import { HistoryActions } from '@/store/history/consts';
import {
  IgnoreActionPayload,
  IgnoreActionType,
  LedgerActionEntry
} from '@/store/history/types';
import store from '@/store/store';
import { ActionStatus, Message } from '@/store/types';
import { useStore } from '@/store/utils';
import { uniqueStrings } from '@/utils/data';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';
import LedgerActionDetails from '@/views/history/LedgerActionDetails.vue';

type GetId<T> = (item: T) => number | undefined;

enum ActionFilterKeys {
  ASSET = 'asset',
  TYPE = 'type',
  START = 'start',
  END = 'end',
  LOCATION = 'location'
}

const tableHeaders: DataTableHeader[] = [
  { text: '', value: 'selection', width: '34px', sortable: false },
  {
    text: i18n.t('ledger_actions.headers.location').toString(),
    value: 'location',
    width: '120px',
    align: 'center'
  },
  {
    text: i18n.t('ledger_actions.headers.type').toString(),
    value: 'actionType'
  },
  {
    text: i18n.t('ledger_actions.headers.asset').toString(),
    value: 'asset'
  },
  {
    text: i18n.t('ledger_actions.headers.amount').toString(),
    value: 'amount'
  },
  {
    text: i18n.t('ledger_actions.headers.date').toString(),
    value: 'timestamp'
  },
  {
    text: i18n.t('ledger_actions.headers.ignored').toString(),
    value: 'ignoredInAccounting'
  },
  {
    text: i18n.t('ledger_actions.headers.actions').toString(),
    align: 'end',
    value: 'actions'
  },
  { text: '', value: 'data-table-expand' }
];

const setupFilter = (
  assets: Ref<string[]>,
  locations: Ref<string[]>,
  items: Ref<LedgerActionEntry[]>,
  visibleItems: Ref<LedgerActionEntry[]>,
  getSymbol: AssetSymbolGetter
) => {
  const filter = ref<MatchedKeyword<ActionFilterKeys>>({});
  const { dateInputFormat } = setupSettings();
  const matchers: Ref<SearchMatcher<ActionFilterKeys>[]> = computed(() => [
    {
      key: ActionFilterKeys.ASSET,
      description: i18n.t('ledger_actions.filter.asset').toString(),
      suggestions: () => assets.value,
      validate: (asset: string) => assets.value.includes(asset)
    },
    {
      key: ActionFilterKeys.TYPE,
      description: i18n.t('ledger_actions.filter.action_type').toString(),
      suggestions: () => [
        'income',
        'loss',
        'donation received',
        'expense',
        'dividends income',
        'airdrop',
        'gift',
        'grant'
      ],
      validate: type =>
        [
          'income',
          'loss',
          'donation received',
          'expense',
          'dividends income',
          'airdrop',
          'gift',
          'grant'
        ].includes(type)
    },
    {
      key: ActionFilterKeys.START,
      description: i18n.t('ledger_actions.filter.start_date').toString(),
      suggestions: () => [],
      hint: i18n
        .t('ledger_actions.filter.date_hint', {
          format: getDateInputISOFormat(dateInputFormat.value)
        })
        .toString(),
      validate: value => {
        return (
          value.length > 0 &&
          !isNaN(convertToTimestamp(value, dateInputFormat.value))
        );
      }
    },
    {
      key: ActionFilterKeys.END,
      description: i18n.t('ledger_actions.filter.end_date').toString(),
      suggestions: () => [],
      hint: i18n
        .t('ledger_actions.filter.date_hint', {
          format: getDateInputISOFormat(dateInputFormat.value)
        })
        .toString(),
      validate: value => {
        return (
          value.length > 0 &&
          !isNaN(convertToTimestamp(value, dateInputFormat.value))
        );
      }
    },
    {
      key: ActionFilterKeys.LOCATION,
      description: i18n.t('ledger_actions.filter.location').toString(),
      suggestions: () => locations.value,
      validate: location => locations.value.includes(location as any)
    }
  ]);

  const applyFilter = () => {
    const assetFilter = filter.value[ActionFilterKeys.ASSET];
    const locationFilter = filter.value[ActionFilterKeys.LOCATION];
    const actionFilter = filter.value[ActionFilterKeys.TYPE];
    const startFilter = filter.value[ActionFilterKeys.START];
    const endFilter = filter.value[ActionFilterKeys.END];

    visibleItems.value = items.value.filter(value => {
      const asset = getSymbol(value.asset);
      const assetMatch = checkIfMatch(asset, assetFilter);
      const locationMatch = checkIfMatch(value.location, locationFilter);
      const actionMatch = checkIfMatch(value.actionType, actionFilter);
      const isStartMatch = startMatch(
        value.timestamp,
        startFilter,
        dateInputFormat.value
      );
      const isEndMatch = endMatch(
        value.timestamp,
        endFilter,
        dateInputFormat.value
      );
      return (
        assetMatch && locationMatch && actionMatch && isStartMatch && isEndMatch
      );
    });
  };

  const updateFilter = (selectedFilter: MatchedKeyword<ActionFilterKeys>) => {
    filter.value = selectedFilter;

    applyFilter();
  };
  watch(items, () => applyFilter());
  onMounted(() => applyFilter());

  return {
    matchers,
    filter,
    applyFilter,
    updateFilter
  };
};

const setupIgnore = (
  selected: Ref<UnwrapRef<number[]>>,
  items: Ref<LedgerActionEntry[]>
) => {
  const setMessage = (message: Message) => {
    store.commit('setMessage', message);
  };
  const ignoreActions = async (payload: IgnoreActionPayload) => {
    return (await store.dispatch(
      `history/${HistoryActions.IGNORE_ACTIONS}`,
      payload
    )) as ActionStatus;
  };

  const unignoreActions = async (payload: IgnoreActionPayload) => {
    return (await store.dispatch(
      `history/${HistoryActions.UNIGNORE_ACTION}`,
      payload
    )) as ActionStatus;
  };
  const ignore = async (ignored: boolean) => {
    const ids = items.value
      .filter(({ identifier, ignoredInAccounting }) => {
        return (
          (ignored ? !ignoredInAccounting : ignoredInAccounting) &&
          selected.value.includes(identifier)
        );
      })
      .map(({ identifier }) => identifier.toString())
      .filter((value, index, array) => array.indexOf(value) === index);

    let status: ActionStatus;

    if (ids.length === 0) {
      const choice = ignored ? 1 : 2;
      setMessage({
        success: false,
        title: i18n.tc('ignore.no_items.title', choice).toString(),
        description: i18n.tc('ignore.no_items.description', choice).toString()
      });
      return;
    }
    const payload: IgnoreActionPayload = {
      actionIds: ids,
      type: IgnoreActionType.LEDGER_ACTIONS
    };
    if (ignored) {
      status = await ignoreActions(payload);
    } else {
      status = await unignoreActions(payload);
    }

    if (status.success) {
      selected.value = [];
    }
  };

  return {
    ignore
  };
};

export default defineComponent({
  name: 'LedgerActionsContent',
  components: {
    TableFilter,
    LedgerActionDetails,
    DataTable,
    IgnoreButtons,
    RefreshButton,
    UpgradeRow,
    RowActions,
    AssetDetails,
    LocationDisplay,
    DateDisplay
  },
  props: {
    items: {
      required: true,
      type: Array as PropType<LedgerActionEntry[]>
    },
    limit: {
      required: true,
      type: Number
    },
    total: {
      required: true,
      type: Number
    },
    refreshing: {
      required: false,
      type: Boolean,
      default: false
    },
    loading: {
      required: false,
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const { items, limit, total } = toRefs(props);
    const visibleItems: Ref<LedgerActionEntry[]> = ref([]);
    const showUpgradeRow = computed(() => {
      return limit.value <= total.value && limit.value > 0;
    });
    const locations = computed(() =>
      items.value.map(({ location }) => location).filter(uniqueStrings)
    );

    const store = useStore();
    const getSymbol = store.getters[
      'balances/assetSymbol'
    ] as AssetSymbolGetter;

    const assets = computed(() => {
      return items.value
        .map(({ asset }) => asset)
        .filter(uniqueStrings)
        .map(id => getSymbol(id));
    });

    const page = ref(1);
    watch(items, (value, oldValue) => {
      if (value.length !== oldValue?.length) {
        page.value = 1;
      }
    });

    const setupSelectionMode = (
      visibleItems: Ref<Array<LedgerActionEntry>>,
      getId: GetId<LedgerActionEntry>
    ) => {
      const selected = ref<number[]>([]);

      const setSelected = (selectAll: boolean) => {
        const selection: number[] = [];
        if (selectAll) {
          for (const item of visibleItems.value) {
            const id = getId(item);
            if (!id || selection.includes(id)) {
              logger.warn(
                'A problematic item has been detected, possible duplicate id',
                item
              );
            } else {
              selection.push(id);
            }
          }
        }
        selected.value = selection;
      };

      const selectionChanged = (identifier: number, select: boolean) => {
        const selection = [...selected.value];
        if (!select) {
          const index = selection.indexOf(identifier);
          if (index >= 0) {
            selection.splice(index, 1);
          }
        } else if (identifier && !selection.includes(identifier)) {
          selection.push(identifier);
        }
        selected.value = selection;
      };

      const allSelected = computed(() => {
        const numbers = visibleItems.value.map(getId);
        return (
          numbers.length > 0 && isEqual(sortBy(numbers), sortBy(selected.value))
        );
      });

      return {
        selected,
        setSelected,
        selectionChanged,
        allSelected
      };
    };

    const selectionMode = setupSelectionMode(
      visibleItems,
      item => item.identifier
    );

    return {
      tableHeaders,
      visibleItems,
      page,
      showUpgradeRow,
      expanded: ref([]),
      ...setupIgnore(selectionMode.selected, items),
      ...setupFilter(assets, locations, items, visibleItems, getSymbol),
      ...selectionMode
    };
  }
});
</script>

<style scoped lang="scss">
::v-deep {
  th {
    &:nth-child(2) {
      span {
        padding-left: 16px;
      }
    }
  }
}
</style>
