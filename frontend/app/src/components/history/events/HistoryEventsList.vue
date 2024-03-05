<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import type { Ref } from 'vue';
import type { HistoryEventEntry } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    eventGroup: HistoryEventEntry;
    allEvents: HistoryEventEntry[];
    colspan: number;
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  (e: 'edit-event', data: HistoryEventEntry): void;
  (
    e: 'delete-event',
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
  if (all.length === 0)
    return [eventHeader];

  const eventIdentifierHeader = eventHeader.eventIdentifier;
  const filtered = all
    .filter(
      ({ eventIdentifier, hidden }) =>
        eventIdentifier === eventIdentifierHeader && !hidden,
    )
    .sort((a, b) => Number(a.sequenceIndex) - Number(b.sequenceIndex));

  if (filtered.length > 0)
    return filtered;

  return [eventHeader];
}, []);

const ignoredInAccounting = useRefMap(
  eventGroup,
  ({ ignoredInAccounting }) => !!ignoredInAccounting,
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
      current.eventIdentifier !== old.eventIdentifier
      || currentIgnored !== oldIgnored
    )
      set(panel, currentIgnored ? [] : [0]);
  },
);

const blockEvent = isEthBlockEventRef(eventGroup);
const [DefineTable, ReuseTable] = createReusableTemplate();
</script>

<template>
  <Fragment>
    <DefineTable>
      <HistoryEventsListTable
        :events="events"
        :block-number="blockEvent?.blockNumber"
        :loading="loading"
        @delete-event="emit('delete-event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
        @edit-event="emit('edit-event', $event)"
      />
    </DefineTable>
    <td
      colspan="1"
      class="px-0"
    />
    <td :colspan="colspan - 1">
      <ReuseTable v-if="!showDropdown" />
      <RuiAccordions
        v-else
        v-model="panel"
        multiple
      >
        <RuiAccordion
          header-class="py-3"
        >
          <template #header="{ open }">
            <div class="text-rui-primary font-bold">
              {{
                open
                  ? t('transactions.events.view.hide')
                  : t('transactions.events.view.show', {
                    length: events.length,
                  })
              }}
            </div>
          </template>
          <div class="-mt-2">
            <ReuseTable />
          </div>
        </RuiAccordion>
      </RuiAccordions>
    </td>
  </Fragment>
</template>
