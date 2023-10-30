<script setup lang="ts">
import { type Ref } from 'vue';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type HistoryEventEntry } from '@/types/history/events';
import { isEvmEvent } from '@/utils/history/events';
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

const { getChain } = useSupportedChains();

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

const blockEvent = isEthBlockEventRef(eventGroup);
const [DefineTable, ReuseTable] = createReusableTemplate();
</script>

<template>
  <Fragment>
    <DefineTable>
      <template v-if="events.length > 0">
        <Fragment>
          <div
            v-for="(item, index) in events"
            :key="index"
            class="grid md:grid-cols-8 py-4 items-center"
            :class="{
              'border-b': index < events.length - 1
            }"
          >
            <HistoryEventType
              :event="item"
              :chain="getChain(item.location)"
              class="md:col-span-2"
            />
            <HistoryEventAsset :event="item" class="md:col-span-2" />
            <HistoryEventNote
              v-bind="item"
              :amount="item.balance.amount"
              :chain="getChain(item.location)"
              :no-tx-hash="isNoTxHash(item)"
              :block-number="blockEvent?.blockNumber"
              class="break-words leading-6 md:col-span-3"
            />
            <RowActions
              class="md:col-span-1"
              align="end"
              :delete-tooltip="t('transactions.events.actions.delete')"
              :edit-tooltip="t('transactions.events.actions.edit')"
              @edit-click="editEvent(item)"
              @delete-click="deleteEvent(item)"
            />
          </div>
        </Fragment>
      </template>

      <template v-else>
        <div v-if="loading || evaluating">
          {{ t('transactions.events.loading') }}
        </div>
        <div v-else>
          {{ t('transactions.events.no_data') }}
        </div>
      </template>
    </DefineTable>
    <td colspan="1" />
    <td :colspan="colspan - 1">
      <ReuseTable v-if="!showDropdown" />
      <VExpansionPanels v-else v-model="panel" flat multiple>
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
