<script setup lang="ts">
import type { ShowEventHistoryForm } from '@/modules/history/management/forms/form-types';
import type { Collection } from '@/types/collection';
import type {
  EvmChainAndTxHash,
  HistoryEventEntry,
  PullEvmTransactionPayload,

} from '@/types/history/events';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import DateDisplay from '@/components/display/DateDisplay.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import LazyLoader from '@/components/helper/LazyLoader.vue';
import HistoryEventsAction from '@/components/history/events/HistoryEventsAction.vue';
import HistoryEventsIdentifier from '@/components/history/events/HistoryEventsIdentifier.vue';
import HistoryEventsList from '@/components/history/events/HistoryEventsList.vue';
import IgnoredInAcountingIcon from '@/components/history/IgnoredInAcountingIcon.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useIgnore } from '@/composables/history';
import { useHistoryEvents } from '@/composables/history/events';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { useStatusStore } from '@/store/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { Section } from '@/types/status';
import { isTaskCancelled } from '@/utils';
import { isAssetMovementEvent } from '@/utils/history/events';
import { HistoryEventEntryType } from '@rotki/common';
import { groupBy } from 'es-toolkit';

interface DeleteOrIgnoreEvent {
  readonly event: HistoryEventEntry;
  readonly mode: 'ignore' | 'delete';
}

const sort = defineModel<DataTableSortData<HistoryEventEntry>>('sort', { required: true });

const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const props = defineProps<{
  groups: Collection<HistoryEventEntry>;
  excludeIgnored: boolean;
  groupLoading: boolean;
  identifiers?: string[];
  highlightedIdentifiers?: string[];
}>();

const emit = defineEmits<{
  'show:form': [payload: ShowEventHistoryForm];
  'set-page': [page: number];
  'refresh': [payload?: PullEvmTransactionPayload];
}>();

defineSlots<{
  'query-status': (props: { colspan: number }) => any;
}>();

const { groupLoading, groups } = toRefs(props);

const eventsLoading = ref(false);
const deleteOrIgnoreEvent = ref<DeleteOrIgnoreEvent>();
const selected = ref<HistoryEventEntry[]>([]);

const { t } = useI18n();

const { notify } = useNotificationsStore();
const { show } = useConfirmStore();
const { isLoading } = useStatusStore();

const { deleteTransactions } = useHistoryEventsApi();
const { deleteHistoryEvent, fetchHistoryEvents } = useHistoryEvents();
const { ignoreSingle, toggle } = useIgnore<HistoryEventEntry>({
  actionType: IgnoreActionType.HISTORY_EVENTS,
  toData: (item: HistoryEventEntry) => item.eventIdentifier,
}, selected, () => {
  emit('refresh');
});

const sectionLoading = isLoading(Section.HISTORY);

const cols = computed<DataTableColumn<HistoryEventEntry>[]>(() => [{
  cellClass: '!p-0 w-px',
  class: '!p-0 w-px',
  key: 'ignoredInAccounting',
  label: '',
}, {
  cellClass: '!py-2',
  key: 'txHash',
  label: t('transactions.events.headers.event_identifier'),
}, {
  align: 'end',
  cellClass: 'text-no-wrap !py-2 w-[12rem]',
  class: 'w-[12rem]',
  key: 'timestamp',
  label: t('common.datetime'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'w-[1.25rem] !py-2',
  class: 'w-[1.25rem]',
  key: 'action',
  label: '',
}, {
  align: 'end',
  cellClass: '!w-0 !p-0',
  class: '!w-0 !p-0',
  key: 'expand',
  label: '',
}]);

const events: Ref<HistoryEventEntry[]> = asyncComputed(async () => {
  const data = get(groups, 'data');

  if (data.length === 0)
    return [];

  const response = await fetchHistoryEvents({
    eventIdentifiers: data.map(item => item.eventIdentifier),
    excludeIgnoredAssets: props.excludeIgnored,
    groupByEventIds: false,
    identifiers: props.identifiers,
    limit: -1,
    offset: 0,
  });

  return response.data;
}, [], {
  evaluating: eventsLoading,
  lazy: true,
});

const eventsGroupedByEventIdentifier = computed<Record<string, HistoryEventEntry[]>>(() => groupBy(get(events), item => item.eventIdentifier));

const loading = refDebounced(logicOr(groupLoading, eventsLoading), 300);
const hasIgnoredEvent = useArraySome(events, event => event.ignoredInAccounting);

function getItemClass(item: HistoryEventEntry): '' | 'opacity-50' {
  return item.ignoredInAccounting ? 'opacity-50' : '';
}

function confirmDelete({ canDelete, item }: { item: HistoryEventEntry; canDelete: boolean }): void {
  set(deleteOrIgnoreEvent, {
    event: item,
    mode: canDelete ? 'delete' : 'ignore',
  });

  let text: { primaryAction: string; title: string; message: string };
  if (!canDelete) {
    text = {
      message: t('transactions.events.confirmation.ignore.message'),
      primaryAction: t('transactions.events.confirmation.ignore.action'),
      title: t('transactions.events.confirmation.ignore.title'),
    };
  }
  else {
    text = {
      message: t('transactions.events.confirmation.delete.message'),
      primaryAction: t('common.actions.confirm'),
      title: t('transactions.events.confirmation.delete.title'),
    };
  }
  show(text, onConfirmDelete, () => {
    set(deleteOrIgnoreEvent, undefined);
  });
}

async function onConfirmDelete(): Promise<void> {
  if (!isDefined(deleteOrIgnoreEvent))
    return;

  const { event, mode } = get(deleteOrIgnoreEvent);

  if (mode === 'ignore') {
    await ignoreSingle(event, true);
  }
  else {
    const ids = [];
    if (isAssetMovementEvent(event) || event.entryType === HistoryEventEntryType.SWAP_EVENT) {
      ids.push(...(get(eventsGroupedByEventIdentifier)[event.eventIdentifier] || []).map(item => item.identifier));
    }
    else {
      ids.push(event.identifier);
    }
    const { success } = await deleteHistoryEvent(ids);
    if (!success)
      return;

    emit('refresh');
  }
}

function suggestNextSequenceId(group: HistoryEventEntry): string {
  const all = get(events);

  if (!all?.length)
    return (Number(group.sequenceIndex) + 1).toString();

  const eventIdentifierHeader = group.eventIdentifier;
  const filtered = all
    .filter(({ eventIdentifier, hidden }) => eventIdentifier === eventIdentifierHeader && !hidden)
    .map(({ sequenceIndex }) => Number(sequenceIndex))
    .sort((a, b) => b - a);

  return ((filtered[0] ?? Number(group.sequenceIndex)) + 1).toString();
}

async function onConfirmTxAndEventDelete({ evmChain, txHash }: EvmChainAndTxHash): Promise<void> {
  try {
    await deleteTransactions(evmChain, txHash);
    emit('refresh');
  }
  catch (error: any) {
    if (isTaskCancelled(error))
      return;

    const title = t('transactions.dialog.delete.error.title');
    const message = t('transactions.dialog.delete.error.message', {
      message: error.message,
    });
    notify({
      display: true,
      message,
      title,
    });
  }
}

function confirmTxAndEventsDelete(payload: EvmChainAndTxHash): void {
  show({
    message: t('transactions.dialog.delete.message'),
    title: t('transactions.dialog.delete.title'),
  }, () => onConfirmTxAndEventDelete(payload));
}

const showRedecodeConfirmation = ref<boolean>(false);
const deleteCustom = ref<boolean>(false);
const redecodePayload = ref<EvmChainAndTxHash>();

function redecode(payload: EvmChainAndTxHash, eventIdentifier: string): void {
  const childEvents = get(eventsGroupedByEventIdentifier)[eventIdentifier] || [];
  const isAnyCustom = childEvents.some(item => item.customized);

  if (!isAnyCustom) {
    emit('refresh', { transactions: [payload] });
  }
  else {
    set(redecodePayload, payload);
    set(showRedecodeConfirmation, true);
    set(deleteCustom, false);
  }
}

function forceRedecode(): void {
  const payload = get(redecodePayload);
  if (payload) {
    emit('refresh', {
      deleteCustom: get(deleteCustom),
      transactions: [payload],
    });
  }
  set(showRedecodeConfirmation, false);
  set(deleteCustom, false);
  set(redecodePayload, undefined);
}
</script>

<template>
  <CollectionHandler
    :collection="groups"
    @set-page="emit('set-page', $event)"
  >
    <template #default="{ data: rows, showUpgradeRow, limit, total, found, entriesFoundTotal }">
      <RuiDataTable
        v-model:pagination.external="pagination"
        v-model:sort.external="sort"
        :expanded="rows"
        :cols="cols"
        :rows="rows"
        :loading="loading"
        :item-class="getItemClass"
        :empty="{ label: t('data_table.no_data') }"
        :texts="{
          rowsPerPage: t('data_table.rows_per_page'),
          itemsNumber: t('data_table.items_no'),
          of: t('common.of'),
        }"
        row-attr="identifier"
        outlined
      >
        <template #item.ignoredInAccounting="{ row }">
          <IgnoredInAcountingIcon
            v-if="row.ignoredInAccounting"
            class="ml-4"
          />
          <div
            v-else
            class="min-h-[3.25rem]"
          />
        </template>
        <template #item.txHash="{ row }">
          <LazyLoader class="flex items-center gap-2.5">
            <LocationIcon
              icon
              :item="row.location"
              size="20px"
            />
            <HistoryEventsIdentifier :event="row" />
          </LazyLoader>
        </template>
        <template #item.timestamp="{ row }">
          <LazyLoader>
            <DateDisplay
              :timestamp="row.timestamp"
              milliseconds
            />
          </LazyLoader>
        </template>
        <template #item.action="{ row }">
          <LazyLoader>
            <HistoryEventsAction
              :event="row"
              :loading="eventsLoading"
              @add-event="emit('show:form', {
                type: 'event',
                data: {
                  type: 'group-add',
                  group: $event,
                  nextSequenceId: suggestNextSequenceId(row),
                },
              })"
              @toggle-ignore="toggle($event)"
              @redecode="redecode($event, row.eventIdentifier)"
              @delete-tx="confirmTxAndEventsDelete($event)"
            />
          </LazyLoader>
        </template>
        <template #item.expand />
        <template #expanded-item="{ row }">
          <HistoryEventsList
            class="-my-4"
            :class="{ 'opacity-50': row.ignoredInAccounting }"
            :all-events="eventsGroupedByEventIdentifier[row.eventIdentifier] || []"
            :event-group="row"
            :loading="sectionLoading || eventsLoading"
            :has-ignored-event="hasIgnoredEvent"
            :highlighted-identifiers="highlightedIdentifiers"
            @edit-event="emit('show:form', {
              type: 'event',
              data: {
                ...$event,
                nextSequenceId: suggestNextSequenceId(row),
              },
            })"
            @delete-event="confirmDelete($event)"
            @show:missing-rule-action="emit('show:form', {
              type: 'missingRule',
              data: {
                ...$event,
                nextSequenceId: suggestNextSequenceId(row),
              },
            })"
          />
        </template>
        <template #body.prepend="{ colspan }">
          <slot
            name="query-status"
            :colspan="colspan"
          />
          <UpgradeRow
            v-if="showUpgradeRow"
            :limit="limit"
            :total="total"
            :found="found"
            :entries-found-total="entriesFoundTotal"
            :colspan="colspan"
            :label="t('common.events')"
          />
        </template>
      </RuiDataTable>
    </template>
  </CollectionHandler>
  <RuiDialog
    v-model="showRedecodeConfirmation"
    :max-width="500"
  >
    <RuiCard
      class="[&>div:first-child]:pb-0"
    >
      <template #header>
        {{ t('transactions.actions.redecode_events') }}
      </template>
      <div class="mb-2">
        {{ t('transactions.events.confirmation.reset.message') }}
      </div>
      <RuiRadioGroup
        v-model="deleteCustom"
        color="primary"
      >
        <RuiRadio :value="false">
          {{ t('transactions.events.confirmation.reset.options.keep_custom_events') }}
        </RuiRadio>
        <RuiRadio :value="true">
          {{ t('transactions.events.confirmation.reset.options.remove_custom_events') }}
        </RuiRadio>
      </RuiRadioGroup>
      <template #footer>
        <div class="grow" />
        <RuiButton
          color="primary"
          @click="forceRedecode()"
        >
          {{ t('common.actions.proceed') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
