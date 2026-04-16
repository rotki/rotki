<script setup lang="ts">
import type { Filters, Matcher } from '@/modules/core/table/filters/use-events-filter';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
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
  fetchData,
  isLoading: groupLoading,
  pageParams,
  pagination,
  setPage,
  sort,
  state: groups,
} = usePaginationFilters<
  HistoryEventRow,
  HistoryEventRequestPayload,
  Filters,
  Matcher
>(fetchHistoryEvents, {
  requestParams: computed(() => ({
    aggregateByGroupIds: true,
    identifiers: get(eventIdentifiers),
  })),
});

onMounted(() => {
  fetchData();
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
        :groups="groups"
        :exclude-ignored="false"
        :group-loading="groupLoading"
        :page-params="pageParams"
        :identifiers="eventIdentifiers"
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
