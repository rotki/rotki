<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import type { ComputedRef } from 'vue';
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

const PER_BATCH = 6;
const currentLimit: Ref<number> = ref(0);

const { t } = useI18n();

const { eventGroup, allEvents } = toRefs(props);

const events: ComputedRef<HistoryEventEntry[]> = computed(() => {
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
});

const ignoredInAccounting = useRefMap(
  eventGroup,
  ({ ignoredInAccounting }) => !!ignoredInAccounting,
);

const showDropdown = computed(() => {
  const length = get(events).length;
  return (get(ignoredInAccounting) || length > PER_BATCH) && length > 0;
});

watch(
  [eventGroup, ignoredInAccounting],
  ([current, currentIgnored], [old, oldIgnored]) => {
    if (
      current.eventIdentifier !== old.eventIdentifier
      || currentIgnored !== oldIgnored
    )
      set(currentLimit, currentIgnored ? 0 : PER_BATCH);
  },
);

const blockEvent = isEthBlockEventRef(eventGroup);
const [DefineTable, ReuseTable] = createReusableTemplate();

const limitedEvents: ComputedRef<HistoryEventEntry[]> = computed(() => {
  const limit = get(currentLimit);
  if (limit === 0)
    return [];

  return [...get(events)].slice(0, limit);
});

function handleMoreClick() {
  const limit = get(currentLimit);
  if (limit < get(events).length)
    set(currentLimit, limit + PER_BATCH);
  else
    set(currentLimit, 0);
}
</script>

<template>
  <Fragment>
    <DefineTable #default="{ data }">
      <HistoryEventsListTable
        :events="data"
        :total="events.length"
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
      <ReuseTable
        v-if="!showDropdown"
        :data="events"
      />
      <RuiAccordions
        v-else
        :value="0"
      >
        <RuiAccordion
          eager
        >
          <template #default>
            <ReuseTable
              :data="limitedEvents"
            />
          </template>
        </RuiAccordion>
      </RuiAccordions>
      <RuiButton
        v-if="showDropdown"
        color="primary"
        variant="text"
        class="text-rui-primary font-bold my-2"
        @click="handleMoreClick()"
      >
        <template v-if="currentLimit === 0">
          {{
            t('transactions.events.view.show', {
              length: events.length,
            })
          }}
        </template>
        <template v-else-if="currentLimit >= events.length">
          {{ t('transactions.events.view.hide') }}
        </template>
        <template v-else>
          {{
            t('transactions.events.view.load_more', {
              length: events.length - currentLimit,
            })
          }}
        </template>
        <template #append>
          <RuiIcon
            class="transition-all"
            name="arrow-down-s-line"
            :class="{ 'transform -rotate-180': currentLimit >= events.length }"
          />
        </template>
      </RuiButton>
    </td>
  </Fragment>
</template>
