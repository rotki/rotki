<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import { type Collection } from '@/types/collection';
import { Routes } from '@/router/routes';
import { type TradeLocation } from '@/types/history/trade/location';
import {
  type LedgerAction,
  type LedgerActionEntry,
  type LedgerActionRequestPayload
} from '@/types/history/ledger-action/ledger-actions';
import { Section } from '@/types/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { SavedFilterLocation } from '@/types/filtering';
import type { Filters, Matcher } from '@/composables/filters/ledger-actions';

const props = withDefaults(
  defineProps<{
    locationOverview?: TradeLocation;
  }>(),
  {
    locationOverview: ''
  }
);

const { locationOverview } = toRefs(props);

const mainPage = computed(() => get(locationOverview) === '');

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

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
      text: t('common.location'),
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: t('common.type'),
      value: 'type'
    },
    {
      text: t('common.asset'),
      value: 'asset',
      sortable: false
    },
    {
      text: t('common.amount'),
      value: 'amount'
    },
    {
      text: t('common.datetime'),
      value: 'timestamp'
    },
    {
      text: t('ledger_actions.headers.actions'),
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

const { deleteLedgerAction, fetchLedgerActions, refreshLedgerActions } =
  useLedgerActions();

const {
  options,
  selected,
  editableItem,
  itemsToDelete: ledgerActionsToDelete,
  confirmationMessage,
  expanded,
  isLoading,
  state: ledgerActions,
  filters,
  matchers,
  setPage,
  setOptions,
  setFilter,
  fetchData
} = usePaginationFilters<
  LedgerAction,
  LedgerActionRequestPayload,
  LedgerActionEntry,
  Collection<LedgerActionEntry>,
  Filters,
  Matcher
>(locationOverview, mainPage, useLedgerActionsFilter, fetchLedgerActions);

const { setOpenDialog, setPostSubmitFunc } = useLedgerActionsForm();

setPostSubmitFunc(fetchData);

const newLedgerAction = () => {
  set(editableItem, null);
  setOpenDialog(true);
};

const editLedgerActionHandler = (ledgerAction: LedgerActionEntry) => {
  set(editableItem, ledgerAction);
  setOpenDialog(true);
};

const promptForDelete = (ledgerAction: LedgerActionEntry) => {
  set(confirmationMessage, t('ledger_actions.delete.message'));
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
    t('ledger_actions.delete.multiple_message', {
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

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.LEDGER_ACTIONS,
    toData: (item: LedgerActionEntry) => item.identifier.toString()
  },
  selected,
  () => fetchData()
);

const { show } = useConfirmStore();

const showDeleteConfirmation = () => {
  show(
    {
      title: t('ledger_actions.delete.title'),
      message: get(confirmationMessage)
    },
    deleteLedgerActionHandler
  );
};

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.LEDGER_ACTIONS);

const getItemClass = (item: LedgerActionEntry) =>
  item.ignoredInAccounting ? 'darken-row' : '';

const pageRoute = Routes.HISTORY_LEDGER_ACTIONS;

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

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});
</script>

<template>
  <TablePageLayout :hide-header="!mainPage">
    <template #title>
      <span class="text-rui-text-secondary">
        {{ t('navigation_menu.history') }} /
      </span>
      {{ t('ledger_actions.title') }}
    </template>
    <template v-if="mainPage" #buttons>
      <RuiTooltip open-delay="400">
        <template #activator>
          <RuiButton
            :loading="loading"
            color="primary"
            variant="outlined"
            @click="refreshLedgerActions(true)"
          >
            <template #prepend>
              <RuiIcon name="restart-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('ledger_actions.refresh_tooltip') }}
      </RuiTooltip>

      <RuiButton
        color="primary"
        data-cy="ledger-actions__add"
        @click="newLedgerAction()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('ledger_actions.dialog.add.title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <template v-if="!mainPage" #header>
        <CardTitle>
          <NavigatorLink :to="{ path: pageRoute }">
            {{ t('ledger_actions.title') }}
          </NavigatorLink>
        </CardTitle>
      </template>

      <HistoryTableActions v-if="mainPage">
        <template #filter>
          <TableFilter
            :matches="filters"
            :matchers="matchers"
            :location="SavedFilterLocation.HISTORY_LEDGER_ACTIONS"
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
          class="flex flex-row items-center gap-2 text-body-2"
        >
          {{ t('ledger_actions.selected', { count: selected.length }) }}
          <RuiButton variant="text" size="sm" @click="selected = []">
            {{ t('common.actions.clear_selection') }}
          </RuiButton>
        </div>
      </HistoryTableActions>

      <CollectionHandler
        :collection="ledgerActions"
        @set-page="setPage($event)"
      >
        <template #default="{ data, limit, total, showUpgradeRow, itemLength }">
          <DataTable
            v-model="selected"
            :expanded.sync="expanded"
            :headers="tableHeaders"
            :items="data"
            :loading="isLoading"
            :loading-text="t('ledger_actions.loading')"
            :options="options"
            :server-items-length="itemLength"
            data-cy="ledger-actions"
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
                <BadgeDisplay v-if="isMobile" color="grey">
                  <VIcon small> mdi-eye-off </VIcon>
                  <span class="ml-2">
                    {{ t('common.ignored_in_accounting') }}
                  </span>
                </BadgeDisplay>
                <VTooltip v-else bottom>
                  <template #activator="{ on }">
                    <BadgeDisplay color="grey" v-on="on">
                      <VIcon small> mdi-eye-off </VIcon>
                    </BadgeDisplay>
                  </template>
                  <span>
                    {{ t('common.ignored_in_accounting') }}
                  </span>
                </VTooltip>
              </div>
            </template>
            <template #item.type="{ item }">
              <EventTypeDisplay
                data-cy="ledger-action-type"
                :event-type="item.actionType"
              />
            </template>
            <template #item.location="{ item }">
              <LocationDisplay
                data-cy="ledger-action-location"
                :identifier="item.location"
              />
            </template>
            <template #item.asset="{ item }">
              <AssetDetails
                data-cy="ledger-action-asset"
                opens-details
                :asset="item.asset"
              />
            </template>
            <template #item.amount="{ item }">
              <AmountDisplay :value="item.amount" />
            </template>
            <template #item.timestamp="{ item }">
              <DateDisplay :timestamp="item.timestamp" />
            </template>
            <template #item.actions="{ item }">
              <RowActions
                :disabled="loading"
                :edit-tooltip="t('ledger_actions.edit_tooltip')"
                :delete-tooltip="t('ledger_actions.delete_tooltip')"
                @edit-click="editLedgerActionHandler(item)"
                @delete-click="promptForDelete(item)"
              />
            </template>
            <template #expanded-item="{ headers, item }">
              <LedgerActionDetails :span="headers.length" :item="item" />
            </template>
            <template v-if="showUpgradeRow" #body.prepend="{ headers }">
              <UpgradeRow
                :limit="limit"
                :total="total"
                :colspan="headers.length"
                :label="t('ledger_actions.label')"
              />
            </template>
          </DataTable>
        </template>
      </CollectionHandler>

      <LedgerActionFormDialog
        :loading="loading"
        :editable-item="editableItem"
      />
    </RuiCard>
  </TablePageLayout>
</template>
