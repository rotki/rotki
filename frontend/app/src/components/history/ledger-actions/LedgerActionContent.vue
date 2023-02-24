<script setup lang="ts">
import dropRight from 'lodash/dropRight';
import { type ComputedRef, type Ref, type UnwrapRef } from 'vue';
import { type DataTableHeader } from 'vuetify';
import isEqual from 'lodash/isEqual';
import { type MaybeRef } from '@vueuse/core';
import Fragment from '@/components/helper/Fragment';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { Routes } from '@/router/routes';
import {
  type LedgerAction,
  type LedgerActionEntry,
  type LedgerActionRequestPayload
} from '@/types/history/ledger-action/ledger-actions';
import { type TradeLocation } from '@/types/history/trade/location';
import { Section } from '@/types/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { type TablePagination } from '@/types/pagination';
import {
  type LocationQuery,
  RouterPaginationOptionsSchema
} from '@/types/route';
import { defaultOptions } from '@/utils/history';
import { type Collection } from '@/types/collection';
import { defaultCollectionState } from '@/utils/collection';

const props = withDefaults(
  defineProps<{
    locationOverview?: TradeLocation;
    readFilterFromRoute?: boolean;
  }>(),
  {
    locationOverview: '',
    readFilterFromRoute: false
  }
);

const { locationOverview, readFilterFromRoute } = toRefs(props);

const selected: Ref<LedgerActionEntry[]> = ref([]);
const options: Ref<TablePagination<LedgerAction>> = ref(defaultOptions());
const dialogTitle: Ref<string> = ref('');
const dialogSubtitle: Ref<string> = ref('');
const openDialog: Ref<boolean> = ref(false);
const editableItem: Ref<LedgerActionEntry | null> = ref(null);
const ledgerActionsToDelete: Ref<LedgerActionEntry[]> = ref([]);
const confirmationMessage: Ref<string> = ref('');
const expanded: Ref<LedgerActionEntry[]> = ref([]);
const userAction: Ref<boolean> = ref(false);

const { deleteLedgerAction, fetchLedgerActions, refreshLedgerActions } =
  useLedgerActionStore();

const { tc } = useI18n();

const pageParams: ComputedRef<LedgerActionRequestPayload> = computed(() => {
  const { itemsPerPage, page, sortBy, sortDesc } = get(options);
  const offset = (page - 1) * itemsPerPage;

  const selectedFilters = get(filters);
  const overview = get(locationOverview);
  if (overview) {
    selectedFilters.location = overview;
  }

  return {
    limit: itemsPerPage,
    offset,
    orderByAttributes: sortBy.length > 0 ? sortBy : ['timestamp'],
    ascending:
      sortDesc.length > 1 ? dropRight(sortDesc).map(bool => !bool) : [false],
    ...(selectedFilters as Partial<LedgerActionRequestPayload>)
  };
});

const tableHeaders = computed<DataTableHeader[]>(() => {
  const headers: DataTableHeader[] = [
    {
      text: '',
      value: 'ignoredInAccounting',
      sortable: false,
      class: 'pa-0',
      cellClass: 'pa-0'
    },
    {
      text: tc('common.location'),
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: tc('common.type'),
      value: 'type'
    },
    {
      text: tc('common.asset'),
      value: 'asset',
      sortable: false
    },
    {
      text: tc('common.amount'),
      value: 'amount'
    },
    {
      text: tc('common.datetime'),
      value: 'timestamp'
    },
    {
      text: tc('ledger_actions.headers.actions'),
      value: 'actions',
      align: 'center',
      sortable: false,
      width: '50'
    },
    { text: '', value: 'data-table-expand', sortable: false }
  ];

  if (get(locationOverview)) {
    headers.splice(9, 1);
    headers.splice(1, 1);
  }

  return headers;
});

const {
  isLoading,
  state: ledgerActions,
  execute
} = useAsyncState<
  Collection<LedgerActionEntry>,
  MaybeRef<LedgerActionRequestPayload>[]
>(args => fetchLedgerActions(args), defaultCollectionState(), {
  immediate: false,
  resetOnExecute: false,
  delay: 0
});

const fetchData = async (): Promise<void> => {
  await execute(0, pageParams);
};

const newLedgerAction = () => {
  set(dialogTitle, tc('ledger_actions.dialog.add.title'));
  set(dialogSubtitle, tc('ledger_actions.dialog.add.subtitle'));
  set(openDialog, true);
};

const editLedgerActionHandler = (ledgerAction: LedgerActionEntry) => {
  set(editableItem, ledgerAction);
  set(dialogTitle, tc('ledger_actions.dialog.edit.title'));
  set(dialogSubtitle, tc('ledger_actions.dialog.edit.subtitle'));
  set(openDialog, true);
};

const promptForDelete = (ledgerAction: LedgerActionEntry) => {
  set(confirmationMessage, tc('ledger_actions.delete.message'));
  set(ledgerActionsToDelete, [ledgerAction]);

  showDeleteConfirmation();
};

const massDelete = () => {
  const selectedVal = get(selected);
  if (selectedVal.length === 1) {
    promptForDelete(selectedVal[0]);
    return;
  }

  set(ledgerActionsToDelete, [...selectedVal]);

  set(
    confirmationMessage,
    tc('ledger_actions.delete.multiple_message', 0, {
      length: get(ledgerActionsToDelete).length
    })
  );

  showDeleteConfirmation();
};

const deleteLedgerActionHandler = async () => {
  const ledgerActionsToDeleteVal = get(ledgerActionsToDelete);
  if (ledgerActionsToDeleteVal.length === 0) {
    return;
  }

  const ids = ledgerActionsToDeleteVal.map(
    ledgerAction => ledgerAction.identifier
  );
  const { success } = await deleteLedgerAction(ids);

  if (!success) {
    return;
  }

  set(ledgerActionsToDelete, []);
  set(confirmationMessage, '');

  const selectedVal = [...get(selected)];
  set(
    selected,
    selectedVal.filter(ledgerActions => !ids.includes(ledgerActions.identifier))
  );
  await fetchData();
};

const router = useRouter();
const route = useRoute();

const { filters, matchers, updateFilter, RouteFilterSchema } =
  useLedgerActionsFilter();

const applyRouteFilter = () => {
  if (!get(readFilterFromRoute)) return;

  const query = get(route).query;
  const parsedOptions = RouterPaginationOptionsSchema.parse(query);
  const parsedFilters = RouteFilterSchema.parse(query);
  updateFilter(parsedFilters);
  set(options, parsedOptions);
};

watch(route, () => {
  set(userAction, false);
  applyRouteFilter();
});

onBeforeMount(() => {
  applyRouteFilter();
});

watch(filters, async (filters, oldFilters) => {
  if (isEqual(filters, oldFilters)) {
    return;
  }

  set(options, { ...get(options), page: 1 });
});

const setPage = (page: number) => {
  set(userAction, true);
  set(options, { ...get(options), page });
};

const setOptions = (newOptions: TablePagination<LedgerAction>) => {
  set(userAction, true);
  set(options, newOptions);
};

const setFilter = (newFilter: UnwrapRef<typeof filters>) => {
  set(userAction, true);
  updateFilter(newFilter);
};

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.LEDGER_ACTIONS,
    toData: (item: LedgerActionEntry) => item.identifier.toString()
  },
  selected,
  () => fetchData()
);

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    newLedgerAction();
    await router.replace({ query: {} });
  } else {
    await fetchData();
    await refreshLedgerActions();
  }
});

const { show } = useConfirmStore();

const showDeleteConfirmation = () => {
  show(
    {
      title: tc('ledger_actions.delete.title'),
      message: get(confirmationMessage)
    },
    deleteLedgerActionHandler
  );
};

const loading = isSectionLoading(Section.LEDGER_ACTIONS);

const getItemClass = (item: LedgerActionEntry) => {
  return item.ignoredInAccounting ? 'darken-row' : '';
};

const pageRoute = Routes.HISTORY_LEDGER_ACTIONS;

const getQuery = (): LocationQuery => {
  const opts = get(options);
  const { itemsPerPage, page, sortBy, sortDesc } = opts;

  const selectedFilters = get(filters);

  const overview = get(locationOverview);
  if (overview) {
    selectedFilters.location = overview;
  }

  return {
    itemsPerPage: itemsPerPage.toString(),
    page: page.toString(),
    sortBy,
    sortDesc: sortDesc.map(x => x.toString()),
    ...selectedFilters
  };
};

watch(pageParams, async (params, op) => {
  if (isEqual(params, op)) {
    return;
  }
  if (get(userAction) && get(readFilterFromRoute)) {
    // Route should only be updated on user action otherwise it messes with
    // forward navigation.
    await router.push({
      query: getQuery()
    });
    set(userAction, false);
  }

  await fetchData();
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});
</script>

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
        class="ledger-actions__add"
        @click="newLedgerAction()"
      >
        <v-icon> mdi-plus </v-icon>
      </v-btn>
      <template #title>
        <refresh-button
          v-if="!locationOverview"
          :loading="loading"
          :tooltip="tc('ledger_actions.refresh_tooltip')"
          @refresh="refreshLedgerActions(true)"
        />
        <navigator-link :to="{ path: pageRoute }" :enabled="!!locationOverview">
          {{ tc('ledger_actions.title') }}
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
              {{ tc('ledger_actions.selected', 0, { count: selected.length }) }}
              <v-btn small text @click="selected = []">
                {{ tc('common.actions.clear_selection') }}
              </v-btn>
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="pb-md-8">
              <table-filter
                :matches="filters"
                :matchers="matchers"
                @update:matches="setFilter($event)"
              />
            </div>
          </v-col>
        </v-row>
      </template>
      <collection-handler :collection="ledgerActions" @set-page="setPage">
        <template #default="{ data, limit, total, showUpgradeRow, itemLength }">
          <data-table
            v-model="selected"
            :expanded.sync="expanded"
            :headers="tableHeaders"
            :items="data"
            :loading="isLoading"
            :loading-text="tc('ledger_actions.loading')"
            :options="options"
            :server-items-length="itemLength"
            class="ledger_actions"
            :single-select="false"
            :show-select="!locationOverview"
            item-key="identifier"
            show-expand
            single-expand
            multi-sort
            :must-sort="false"
            :item-class="getItemClass"
            @update:options="setOptions($event)"
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
            <template #item.type="{ item }">
              <event-type-display
                data-cy="ledger-action-type"
                :event-type="item.actionType"
              />
            </template>
            <template #item.location="{ item }">
              <location-display
                data-cy="ledger-action-location"
                :identifier="item.location"
              />
            </template>
            <template #item.asset="{ item }">
              <asset-details
                data-cy="ledger-action-asset"
                opens-details
                :asset="item.asset"
              />
            </template>
            <template #item.amount="{ item }">
              <amount-display :value="item.amount" />
            </template>
            <template #item.timestamp="{ item }">
              <date-display :timestamp="item.timestamp" />
            </template>
            <template #item.actions="{ item }">
              <row-actions
                :disabled="loading"
                :edit-tooltip="tc('ledger_actions.edit_tooltip')"
                :delete-tooltip="tc('ledger_actions.delete_tooltip')"
                @edit-click="editLedgerActionHandler(item)"
                @delete-click="promptForDelete(item)"
              />
            </template>
            <template #expanded-item="{ headers, item }">
              <ledger-action-details :span="headers.length" :item="item" />
            </template>
            <template v-if="showUpgradeRow" #body.prepend="{ headers }">
              <upgrade-row
                :limit="limit"
                :total="total"
                :colspan="headers.length"
                :label="tc('ledger_actions.label')"
              />
            </template>
          </data-table>
        </template>
      </collection-handler>
    </card>

    <ledger-action-form-dialog
      :loading="loading"
      :edit="!!editableItem"
      :form-data="editableItem"
      :open="openDialog"
      @update:open="openDialog = $event"
      @reset-edit="editableItem = null"
      @saved="fetchData()"
    />
  </fragment>
</template>
