<script setup lang="ts">
import { type Ref } from 'vue';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type DataTableHeader } from '@/types/vuetify';
import { type HistoryEventEntry } from '@/types/history/events';
import { isEvmEvent } from '@/utils/history/events';
import { type TablePagination } from '@/types/pagination';
import Fragment from '@/components/helper/Fragment';

const props = withDefaults(
  defineProps<{
    eventGroup: HistoryEventEntry;
    allEvents: HistoryEventEntry[];
    colspan: number;
    loading?: boolean;
  }>(),
  {
    loading: false
  }
);

const emit = defineEmits<{
  (e: 'edit:event', data: HistoryEventEntry): void;
  (
    e: 'delete:event',
    data: {
      canDelete: boolean;
      item: HistoryEventEntry;
    }
  ): void;
}>();

const { t } = useI18n();

const { eventGroup, allEvents } = toRefs(props);

const css = useCssModule();

const { getChain } = useSupportedChains();

const headers: DataTableHeader[] = [
  {
    text: t('common.type'),
    value: 'type',
    sortable: false,
    cellClass: css['row__type']
  },
  {
    text: t('common.asset'),
    value: 'asset',
    sortable: false
  },
  {
    text: t('common.description'),
    value: 'description',
    sortable: false,
    cellClass: css['row__description']
  },
  {
    text: '',
    value: 'actions',
    align: 'end',
    sortable: false,
    cellClass: css['row__actions']
  }
];

const evaluating: Ref<boolean> = ref(false);

const events: Ref<HistoryEventEntry[]> = asyncComputed(() => {
  const all = get(allEvents);
  const eventHeader = get(eventGroup);
  if (all.length === 0) {
    return [eventHeader];
  }
  const eventIdentifierHeader = eventHeader.eventIdentifier;
  const filtered = all
    .filter(
      ({ eventIdentifier, hidden }) =>
        eventIdentifier === eventIdentifierHeader && !hidden
    )
    .sort((a, b) => Number(a.sequenceIndex) - Number(b.sequenceIndex));

  if (filtered.length > 0) {
    return filtered;
  }

  return [eventHeader];
}, []);

const editEvent = (item: HistoryEventEntry) => emit('edit:event', item);
const deleteEvent = (item: HistoryEventEntry) =>
  emit('delete:event', {
    item,
    canDelete: isEvmEvent(item) ? get(events).length > 1 : true
  });

const ignoredInAccounting = useRefMap(
  eventGroup,
  ({ ignoredInAccounting }) => !!ignoredInAccounting
);

const panel: Ref<number[]> = ref(get(ignoredInAccounting) ? [] : [0]);

const isNoTxHash = (item: HistoryEventEntry) =>
  item.entryType === HistoryEventEntryType.EVM_EVENT &&
  ((item.counterparty === 'eth2' && item.eventSubtype === 'deposit asset') ||
    (item.counterparty === 'gitcoin' && item.eventSubtype === 'apply') ||
    item.counterparty === 'safe-multisig');

const options: TablePagination<HistoryEventEntry> = {
  itemsPerPage: -1,
  page: 1,
  sortBy: [],
  sortDesc: []
};

const showDropdown = computed(() => {
  const length = get(events).length;
  return (get(ignoredInAccounting) || length > 10) && length > 0;
});

watch(
  [eventGroup, ignoredInAccounting],
  ([current, currentIgnored], [old, oldIgnored]) => {
    if (
      current.eventIdentifier !== old.eventIdentifier ||
      currentIgnored !== oldIgnored
    ) {
      set(panel, currentIgnored ? [] : [0]);
    }
  }
);

const { xs } = useDisplay();
const blockEvent = isEthBlockEventRef(eventGroup);
const [DefineTable, ReuseTable] = createReusableTemplate();
</script>

<template>
  <Fragment>
    <DefineTable>
      <DataTable
        :class="css.table"
        :headers="headers"
        :items="events"
        :loading="loading || evaluating"
        :loading-text="t('transactions.events.loading')"
        :no-data-text="t('transactions.events.no_data')"
        :options="options"
        hide-default-footer
        disable-floating-header
        :hide-default-header="!xs"
      >
        <template #progress><span /></template>
        <template #item.type="{ item }">
          <HistoryEventType :event="item" :chain="getChain(item.location)" />
        </template>
        <template #item.asset="{ item }">
          <HistoryEventAsset :event="item" />
        </template>
        <template #item.description="{ item }">
          <HistoryEventNote
            v-bind="item"
            :amount="item.balance.amount"
            :chain="getChain(item.location)"
            :no-tx-hash="isNoTxHash(item)"
            :block-number="item.blockNumber ?? blockEvent?.blockNumber"
          />
        </template>
        <template #item.actions="{ item }">
          <RowActions
            align="end"
            :delete-tooltip="t('transactions.events.actions.delete')"
            :edit-tooltip="t('transactions.events.actions.edit')"
            @edit-click="editEvent(item)"
            @delete-click="deleteEvent(item)"
          />
        </template>
      </DataTable>
    </DefineTable>
    <td colspan="1" />
    <td :colspan="colspan - 1">
      <ReuseTable v-if="!showDropdown" />
      <VExpansionPanels
        v-else
        v-model="panel"
        flat
        :class="css['expansions-panels']"
        multiple
      >
        <VExpansionPanel class="!bg-transparent !p-0">
          <VExpansionPanelHeader
            v-if="showDropdown"
            class="!w-auto !p-0 !h-12 !min-h-[3rem]"
          >
            <template #default="{ open }">
              <div class="primary--text font-bold">
                {{
                  open
                    ? t('transactions.events.view.hide')
                    : t('transactions.events.view.show', {
                        length: events.length
                      })
                }}
              </div>
            </template>
          </VExpansionPanelHeader>
          <VExpansionPanelContent class="!p-0 [&>*:first-child]:!p-0">
            <ReuseTable />
          </VExpansionPanelContent>
        </VExpansionPanel>
      </VExpansionPanels>
    </td>
  </Fragment>
</template>

<style lang="scss" module>
.table {
  :global {
    .v-data-table {
      &__wrapper {
        tbody {
          tr {
            &:hover {
              @apply bg-transparent #{!important};
            }

            td {
              @apply py-4 #{!important};

              @media screen and (max-width: 599px) {
                @apply px-0 #{!important};
              }
            }
          }
        }
        @apply overflow-x-hidden;
      }
      @apply border-0 bg-transparent #{!important};
    }
  }
}

.row {
  &__type {
    width: 250px;
    @apply pl-0 #{!important};
  }

  &__description {
    width: 40%;
    min-width: 300px;
    line-height: 1.5rem;
    word-break: break-word;
  }

  &__actions {
    width: 100px;
    @apply pr-0 #{!important};
  }
}
</style>
