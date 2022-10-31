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
          @refresh="fetch(true)"
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
        class="ledger_actions"
        :single-select="false"
        :show-select="!locationOverview"
        item-key="identifier"
        show-expand
        single-expand
        multi-sort
        :must-sort="false"
        :item-class="getClass"
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
    </card>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :primary-action="tc('common.actions.save')"
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
      :display="ledgerActionsToDelete.length > 0"
      :title="tc('ledger_actions.delete.title')"
      confirm-type="warning"
      :message="confirmationMessage"
      @cancel="ledgerActionsToDelete = []"
      @confirm="deleteLedgerActionHandler()"
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
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LedgerActionDetails from '@/components/history/ledger-actions/LedgerActionDetails.vue';
import LedgerActionForm from '@/components/history/LedgerActionForm.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { isSectionLoading } from '@/composables/common';
import { useLedgerActionsFilter } from '@/composables/filters/ledger-actions';
import { setupIgnore } from '@/composables/history';
import { useRoute, useRouter } from '@/composables/router';
import { Routes } from '@/router/routes';
import { useLedgerActions } from '@/store/history/ledger-actions';
import { IgnoreActionType, LedgerActionEntry } from '@/store/history/types';
import { Collection } from '@/types/collection';
import {
  LedgerAction,
  LedgerActionRequestPayload,
  NewLedgerAction
} from '@/types/history/ledger-actions';
import { TradeLocation } from '@/types/history/trade-location';
import { Section } from '@/types/status';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof LedgerAction)[];
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

const options: Ref<PaginationOptions | null> = ref(null);
const dialogTitle: Ref<string> = ref('');
const dialogSubtitle: Ref<string> = ref('');
const openDialog: Ref<boolean> = ref(false);
const editableItem: Ref<LedgerActionEntry | null> = ref(null);
const ledgerActionsToDelete: Ref<LedgerActionEntry[]> = ref([]);
const confirmationMessage: Ref<string> = ref('');
const expanded: Ref<LedgerActionEntry[]> = ref([]);
const valid: Ref<boolean> = ref(false);
const form = ref<InstanceType<typeof LedgerActionForm> | null>(null);

const fetch = (refresh: boolean = false) => emit('fetch', refresh);

const ledgerActionStore = useLedgerActions();
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
const { filters, matchers, updateFilter } = useLedgerActionsFilter();

const { tc } = useI18n();

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

const saveData = async (ledgerAction: NewLedgerAction | LedgerActionEntry) => {
  if ((<LedgerActionEntry>ledgerAction).identifier) {
    return await editLedgerAction(ledgerAction as LedgerActionEntry);
  }
  return await addLedgerAction(ledgerAction as NewLedgerAction);
};

const updatePayloadHandler = async () => {
  let paginationOptions = {};

  const optionsVal = get(options);
  if (optionsVal) {
    const { itemsPerPage, page, sortBy, sortDesc } = get(options)!;
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

  const payload: Partial<LedgerActionRequestPayload> = {
    ...(get(filters) as Partial<LedgerActionRequestPayload>),
    ...paginationOptions
  };

  await updateLedgerActionsPayload(payload);
};

const updatePaginationHandler = async (
  newOptions: PaginationOptions | null
) => {
  set(options, newOptions);
  await updatePayloadHandler();
};

watch(filters, async (filter, oldValue) => {
  if (filter === oldValue) {
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

const getId = (item: LedgerActionEntry) => item.identifier.toString();
const selected: Ref<LedgerActionEntry[]> = ref([]);

const pageRoute = Routes.HISTORY_LEDGER_ACTIONS;

const router = useRouter();
const route = useRoute();

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    newLedgerAction();
    await router.replace({ query: {} });
  }
});

let tableHeaders = computed<DataTableHeader[]>(() => {
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

const getClass = (item: LedgerActionEntry) => {
  return item.ignoredInAccounting ? 'darken-row' : '';
};
const loading = isSectionLoading(Section.LEDGER_ACTIONS);

const { ignore } = setupIgnore(
  IgnoreActionType.LEDGER_ACTIONS,
  selected,
  fetch,
  getId
);
</script>
