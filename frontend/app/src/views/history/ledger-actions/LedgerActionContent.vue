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
          :tooltip="$t('ledger_actions.refresh_tooltip')"
          @refresh="fetch(true)"
        />
        <navigator-link :to="{ path: pageRoute }" :enabled="!!locationOverview">
          {{ $t('ledger_actions.title') }}
        </navigator-link>
      </template>
      <template #actions>
        <v-row v-if="!locationOverview">
          <v-col cols="12" sm="6">
            <ignore-buttons
              :disabled="selected.length === 0 || loading"
              @ignore="ignore"
            />
            <div v-if="selected.length > 0" class="mt-2 ms-1">
              {{ $t('ledger_actions.selected', { count: selected.length }) }}
              <v-btn small text @click="selected = []">
                {{ $t('ledger_actions.clear_selection') }}
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
        :loading="loading"
        :options="options"
        :server-items-length="itemLength"
        class="ledger_actions"
        :single-select="false"
        :show-select="!locationOverview"
        item-key="identifier"
        show-expand
        single-expand
        :item-class="item => (item.ignoredInAccounting ? 'darken-row' : '')"
        @update:options="updatePaginationHandler($event)"
      >
        <template #item.ignoredInAccounting="{ item, isMobile }">
          <div v-if="item.ignoredInAccounting">
            <badge-display v-if="isMobile" color="grey">
              <v-icon small> mdi-eye-off </v-icon>
              <span class="ml-2">
                {{ $t('ledger_actions.headers.ignored') }}
              </span>
            </badge-display>
            <v-tooltip v-else bottom>
              <template #activator="{ on }">
                <badge-display color="grey" v-on="on">
                  <v-icon small> mdi-eye-off </v-icon>
                </badge-display>
              </template>
              <span>
                {{ $t('ledger_actions.headers.ignored') }}
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
            :edit-tooltip="$t('ledger_actions.edit_tooltip')"
            :delete-tooltip="$t('ledger_actions.delete_tooltip')"
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
            :label="$t('ledger_actions.label')"
          />
        </template>
      </data-table>
    </card>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :primary-action="$t('ledger_actions.dialog.save')"
      :action-disabled="loading || !valid"
      @confirm="confirmSave()"
      @cancel="clearDialog()"
    >
      <ledger-action-form
        ref="form"
        v-model="valid"
        :edit="editableItem"
        :save-data="saveData"
      />
    </big-dialog>
    <confirm-dialog
      :display="ledgerActionToDelete !== null"
      :title="$t('ledger_actions.delete.title')"
      confirm-type="warning"
      :message="confirmationMessage"
      @cancel="ledgerActionToDelete = null"
      @confirm="deleteLedgerActionHandler()"
    />
  </fragment>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  Ref,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
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
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import {
  MatchedKeyword,
  SearchMatcher
} from '@/components/history/filtering/types';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LedgerActionForm, {
  LedgerActionFormInstance
} from '@/components/history/LedgerActionForm.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { isSectionLoading, useRoute, useRouter } from '@/composables/common';
import {
  getCollectionData,
  setupEntryLimit,
  setupIgnore
} from '@/composables/history';
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import {
  LedgerAction,
  LedgerActionRequestPayload,
  NewLedgerAction,
  TradeLocation
} from '@/services/history/types';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section } from '@/store/const';
import { useHistory, useLedgerActions } from '@/store/history';
import { IgnoreActionType, LedgerActionEntry } from '@/store/history/types';
import { Collection } from '@/types/collection';
import { LedgerActionType } from '@/types/ledger-actions';
import { uniqueStrings } from '@/utils/data';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';
import LedgerActionDetails from '@/views/history/ledger-actions/LedgerActionDetails.vue';

enum LedgerActionFilterKeys {
  ASSET = 'asset',
  TYPE = 'type',
  START = 'start',
  END = 'end',
  LOCATION = 'location'
}

enum LedgerActionFilterValueKeys {
  ASSET = 'asset',
  TYPE = 'type',
  START = 'fromTimestamp',
  END = 'toTimestamp',
  LOCATION = 'location'
}

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof LedgerAction)[];
  sortDesc: boolean[];
};

const tableHeaders = (locationOverview: string): DataTableHeader[] => {
  const headers: DataTableHeader[] = [
    {
      text: '',
      value: 'ignoredInAccounting',
      sortable: false,
      class: 'pa-0',
      cellClass: 'pa-0'
    },
    {
      text: i18n.t('ledger_actions.headers.location').toString(),
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: i18n.t('ledger_actions.headers.type').toString(),
      value: 'type'
    },
    {
      text: i18n.t('ledger_actions.headers.asset').toString(),
      value: 'asset',
      sortable: false
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
      text: i18n.t('ledger_actions.headers.actions').toString(),
      value: 'actions',
      align: 'center',
      sortable: false,
      width: '50'
    },
    { text: '', value: 'data-table-expand', sortable: false }
  ];

  if (locationOverview) {
    headers.splice(9, 1);
    headers.splice(1, 1);
  }

  return headers;
};

export default defineComponent({
  name: 'LedgerActionContent',
  components: {
    NavigatorLink,
    BadgeDisplay,
    RowActions,
    LedgerActionDetails,
    TableFilter,
    DataTable,
    Fragment,
    IgnoreButtons,
    RefreshButton,
    UpgradeRow,
    DateDisplay,
    LocationDisplay,
    LedgerActionForm,
    ConfirmDialog,
    BigDialog
  },
  props: {
    locationOverview: {
      required: false,
      type: String as PropType<TradeLocation | ''>,
      default: ''
    }
  },
  emits: ['fetch'],
  setup(props, { emit }) {
    const { locationOverview } = toRefs(props);

    const fetch = (refresh: boolean = false) => emit('fetch', refresh);

    const historyStore = useHistory();
    const ledgerActionStore = useLedgerActions();
    const assetInfoRetrievalStore = useAssetInfoRetrieval();
    const { supportedAssets } = toRefs(assetInfoRetrievalStore);
    const { getAssetSymbol, getAssetIdentifierForSymbol } =
      assetInfoRetrievalStore;

    const { associatedLocations } = storeToRefs(historyStore);
    const { ledgerActions } = storeToRefs(ledgerActionStore);
    const {
      addLedgerAction,
      editLedgerAction,
      deleteLedgerAction,
      updateLedgerActionsPayload
    } = ledgerActionStore;

    const { data, limit, found, total } = getCollectionData<LedgerActionEntry>(
      ledgerActions as Ref<Collection<LedgerActionEntry>>
    );

    const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total);

    const dialogTitle: Ref<string> = ref('');
    const dialogSubtitle: Ref<string> = ref('');
    const openDialog: Ref<boolean> = ref(false);
    const editableItem: Ref<LedgerActionEntry | null> = ref(null);
    const ledgerActionToDelete: Ref<LedgerActionEntry | null> = ref(null);
    const confirmationMessage: Ref<string> = ref('');
    const expanded: Ref<LedgerActionEntry[]> = ref([]);
    const valid: Ref<boolean> = ref(false);
    const form = ref<LedgerActionFormInstance | null>(null);

    const newLedgerAction = () => {
      set(dialogTitle, i18n.t('ledger_actions.dialog.add.title').toString());
      set(
        dialogSubtitle,
        i18n.t('ledger_actions.dialog.add.subtitle').toString()
      );
      set(openDialog, true);
    };

    const editLedgerActionHandler = (ledgerAction: LedgerActionEntry) => {
      set(editableItem, ledgerAction);
      set(dialogTitle, i18n.t('ledger_actions.dialog.edit.title').toString());
      set(
        dialogSubtitle,
        i18n.t('ledger_actions.dialog.edit.subtitle').toString()
      );
      set(openDialog, true);
    };

    const promptForDelete = (ledgerAction: LedgerActionEntry) => {
      set(
        confirmationMessage,
        i18n.t('ledger_actions.delete.message').toString()
      );
      set(ledgerActionToDelete, ledgerAction);
    };

    const deleteLedgerActionHandler = async () => {
      if (!get(ledgerActionToDelete)) {
        return;
      }

      const { success } = await deleteLedgerAction(
        get(ledgerActionToDelete)!.identifier!
      );

      if (!success) {
        return;
      }

      set(ledgerActionToDelete, null);
      set(confirmationMessage, '');
      fetch();
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

    const saveData = async (
      ledgerAction: NewLedgerAction | LedgerActionEntry
    ) => {
      if ((<LedgerActionEntry>ledgerAction).identifier) {
        return await editLedgerAction(ledgerAction as LedgerActionEntry);
      }
      return await addLedgerAction(ledgerAction as NewLedgerAction);
    };

    const { dateInputFormat } = setupSettings();

    const options: Ref<PaginationOptions | null> = ref(null);
    const filters: Ref<MatchedKeyword<LedgerActionFilterValueKeys>> = ref({});

    const availableAssets = computed<string[]>(() => {
      return get(supportedAssets)
        .map(value => getAssetSymbol(value.identifier))
        .filter(uniqueStrings);
    });

    const availableLocations = computed<TradeLocation[]>(() => {
      return get(associatedLocations);
    });

    const matchers = computed<
      SearchMatcher<LedgerActionFilterKeys, LedgerActionFilterValueKeys>[]
    >(() => [
      {
        key: LedgerActionFilterKeys.ASSET,
        keyValue: LedgerActionFilterValueKeys.ASSET,
        description: i18n.t('ledger_actions.filter.asset').toString(),
        suggestions: () => get(availableAssets),
        validate: (asset: string) => get(availableAssets).includes(asset),
        transformer: (asset: string) => getAssetIdentifierForSymbol(asset) ?? ''
      },
      {
        key: LedgerActionFilterKeys.TYPE,
        keyValue: LedgerActionFilterValueKeys.TYPE,
        description: i18n.t('ledger_actions.filter.action_type').toString(),
        suggestions: () => [...Object.values(LedgerActionType)],
        validate: type =>
          ([...Object.values(LedgerActionType)] as string[]).includes(type)
      },
      {
        key: LedgerActionFilterKeys.START,
        keyValue: LedgerActionFilterValueKeys.START,
        description: i18n.t('ledger_actions.filter.start_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('ledger_actions.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, get(dateInputFormat)))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, get(dateInputFormat)).toString()
      },
      {
        key: LedgerActionFilterKeys.END,
        keyValue: LedgerActionFilterValueKeys.END,
        description: i18n.t('ledger_actions.filter.end_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('ledger_actions.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, get(dateInputFormat)))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, get(dateInputFormat)).toString()
      },
      {
        key: LedgerActionFilterKeys.LOCATION,
        keyValue: LedgerActionFilterValueKeys.LOCATION,
        description: i18n.t('ledger_actions.filter.location').toString(),
        suggestions: () => get(availableLocations),
        validate: location => get(availableLocations).includes(location as any)
      }
    ]);

    const updatePayloadHandler = () => {
      let paginationOptions = {};

      const optionsVal = get(options);
      if (optionsVal) {
        set(options, {
          ...optionsVal,
          sortBy: optionsVal.sortBy.length > 0 ? [optionsVal.sortBy[0]] : [],
          sortDesc:
            optionsVal.sortDesc.length > 0 ? [optionsVal.sortDesc[0]] : []
        });

        const { itemsPerPage, page, sortBy, sortDesc } = get(options)!;
        const offset = (page - 1) * itemsPerPage;

        paginationOptions = {
          limit: itemsPerPage,
          offset,
          orderByAttribute: sortBy.length > 0 ? sortBy[0] : 'timestamp',
          ascending: !sortDesc[0]
        };
      }

      if (get(locationOverview)) {
        filters.value.location = get(locationOverview) as TradeLocation;
      }

      const payload: Partial<LedgerActionRequestPayload> = {
        ...(get(filters) as Partial<LedgerActionRequestPayload>),
        ...paginationOptions
      };

      updateLedgerActionsPayload(payload);
    };

    const updatePaginationHandler = (newOptions: PaginationOptions | null) => {
      set(options, newOptions);
      updatePayloadHandler();
    };

    const updateFilterHandler = (
      newFilters: MatchedKeyword<LedgerActionFilterKeys>
    ) => {
      set(filters, newFilters);

      let newOptions = null;
      if (get(options)) {
        newOptions = {
          ...get(options)!,
          page: 1
        };
      }

      updatePaginationHandler(newOptions);
    };

    const getId = (item: LedgerActionEntry) => item.identifier.toString();
    const selected: Ref<LedgerActionEntry[]> = ref([]);

    const pageRoute = Routes.HISTORY_LEDGER_ACTIONS.route;

    const router = useRouter();
    const route = useRoute();

    onMounted(() => {
      const query = get(route).query;

      if (query.add) {
        newLedgerAction();
        router.replace({ query: {} });
      }
    });

    return {
      pageRoute,
      selected,
      tableHeaders: tableHeaders(get(locationOverview)),
      data,
      limit,
      found,
      total,
      itemLength,
      fetch,
      showUpgradeRow,
      loading: isSectionLoading(Section.LEDGER_ACTIONS),
      dialogTitle,
      dialogSubtitle,
      openDialog,
      editableItem,
      ledgerActionToDelete,
      confirmationMessage,
      expanded,
      valid,
      newLedgerAction,
      editLedgerActionHandler,
      promptForDelete,
      deleteLedgerActionHandler,
      form,
      clearDialog,
      confirmSave,
      saveData,
      options,
      matchers,
      updatePaginationHandler,
      updateFilterHandler,
      ...setupIgnore(
        IgnoreActionType.LEDGER_ACTIONS,
        selected,
        data,
        fetch,
        getId
      )
    };
  }
});
</script>
