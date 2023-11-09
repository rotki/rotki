<script setup lang="ts">
import { type Ref } from 'vue';
import { type HistoryEventEntry } from '@/types/history/events';
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
  (e: 'show:missing-rule-action', data: HistoryEventEntry): void;
}>();

const { t } = useI18n();

const { eventGroup, allEvents } = toRefs(props);

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

const ignoredInAccounting = useRefMap(
  eventGroup,
  ({ ignoredInAccounting }) => !!ignoredInAccounting
);

const panel: Ref<number[]> = ref(get(ignoredInAccounting) ? [] : [0]);

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
</script>

<template>
  <Fragment>
    <td colspan="1" />
    <td :colspan="colspan - 1">
      <HistoryEventsListTable
        v-if="!showDropdown"
        :events="events"
        :block-number="blockEvent?.blockNumber"
        :loading="loading"
        @delete:event="emit('delete:event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
        @edit:event="emit('edit:event', $event)"
      />
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
            <HistoryEventsListTable
              v-if="showDropdown"
              :events="events"
              :block-number="blockEvent?.blockNumber"
              :loading="loading"
              @delete:event="emit('delete:event', $event)"
              @show:missing-rule-action="
                emit('show:missing-rule-action', $event)
              "
              @edit:event="emit('edit:event', $event)"
            />
          </VExpansionPanelContent>
        </VExpansionPanel>
      </VExpansionPanels>
    </td>
  </Fragment>
</template>
