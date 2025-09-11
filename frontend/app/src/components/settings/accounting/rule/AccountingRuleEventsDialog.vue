<script setup lang="ts">
import type { Filters, Matcher } from '@/composables/filters/events';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/types/history/events/schemas';
import { useHistoryEvents } from '@/composables/history/events';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import HistoryEventsTable from '@/modules/history/events/components/HistoryEventsTable.vue';

interface Props {
  eventIds: number[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const display = ref<boolean>(true);

const { fetchHistoryEvents } = useHistoryEvents();

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
    groupByEventIds: true,
    identifiers: props.eventIds.map(id => id.toString()),
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

      <HistoryEventsTable
        v-model:sort="sort"
        v-model:pagination="pagination"
        :groups="groups"
        :exclude-ignored="false"
        :group-loading="groupLoading"
        :page-params="pageParams"
        :identifiers="eventIds.map(id => id.toString())"
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
