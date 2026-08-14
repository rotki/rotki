<script setup lang="ts">
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableSource } from '@/modules/history/events/types';
import type { Filters } from '@/modules/history/events/use-events-filter';
import { useServerTable } from '@/modules/core/table/use-server-table';
import HistoryEventsVirtualTable from '@/modules/history/events/components/HistoryEventsVirtualTable.vue';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';

interface Props {
  eventIds: number[];
}

const { eventIds } = defineProps<Props>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const display = ref<boolean>(true);

const { fetchHistoryEvents } = useHistoryEvents();

const eventIdentifiers = computed<string[]>(() => eventIds.map(id => id.toString()));

const {
  collection: groups,
  isLoading: groupLoading,
  pagination,
  refetch,
  requestPayload,
  setPage,
  sort,
} = useServerTable<
  HistoryEventRow,
  HistoryEventRequestPayload,
  Filters
>({
  fetch: fetchHistoryEvents,
  params: [{
    skipEmpty: true,
    to: 'request',
    values: computed(() => ({
      aggregateByGroupIds: true,
      identifiers: get(eventIdentifiers),
    })),
  }],
});

const source = computed<HistoryEventsTableSource>(() => ({
  excludeIgnored: false,
  groupLoading: get(groupLoading),
  groups: get(groups),
  identifiers: get(eventIdentifiers),
  requestPayload: get(requestPayload),
}));

onMounted(() => {
  refetch();
});

watch(display, (value) => {
  if (!value) {
    emit('close');
  }
});
</script>

<template>
  <RuiDialog
    v-model="display"
    max-width="1200"
  >
    <RuiCard>
      <template #header>
        {{ t('accounting_settings.rule.events_dialog.title', { count: eventIds.length }) }}
      </template>

      <HistoryEventsVirtualTable
        v-model:sort="sort"
        v-model:pagination="pagination"
        hide-actions
        :source="source"
        @set-page="setPage($event)"
      />

      <template #footer>
        <div class="grow" />
        <RuiButton
          color="primary"
          @click="display = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
