<script setup lang="ts">
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { HistoryEventEntry } from '@/types/history/events/schemas';

const sort = defineModel<DataTableSortData<HistoryEventEntry>>('sort', { required: true });
const pagination = defineModel<TablePaginationData>('pagination', { required: true });

defineProps<{
  loading?: boolean;
  total: number;
  found: number;
}>();

const { t } = useI18n({ useScope: 'global' });

function getSortArray() {
  const sortData = get(sort);
  return Array.isArray(sortData) ? sortData : (sortData ? [sortData] : []);
}

const sortColumn = computed<'timestamp' | undefined>({
  get() {
    const sortArray = getSortArray();
    if (sortArray.length === 0)
      return undefined;
    return sortArray[0]?.column as 'timestamp' | undefined;
  },
  set(column: 'timestamp' | undefined) {
    if (!column) {
      set(sort, []);
      return;
    }
    const sortArray = getSortArray();
    const currentDirection = sortArray[0]?.direction ?? 'desc';
    const newDirection = sortArray[0]?.column === column
      ? (currentDirection === 'asc' ? 'desc' : 'asc')
      : 'desc';
    set(sort, [{ column, direction: newDirection }]);
  },
});

const sortDirection = computed<'asc' | 'desc'>(() => {
  const sortArray = getSortArray();
  return sortArray[0]?.direction ?? 'desc';
});

function toggleSort(): void {
  set(sortColumn, 'timestamp');
}

const currentPage = computed<number>({
  get() {
    return get(pagination).page ?? 1;
  },
  set(page: number) {
    set(pagination, { ...get(pagination), page });
  },
});

const itemsPerPage = computed<number>({
  get() {
    return get(pagination).limit ?? 10;
  },
  set(limit: number) {
    set(pagination, { ...get(pagination), limit, page: 1 });
  },
});

const totalPages = computed<number>(() => {
  const perPage = get(itemsPerPage);
  return Math.ceil(get(pagination).total / perPage);
});

const limits = [10, 25, 50, 100];
</script>

<template>
  <div class="flex items-center justify-between gap-4 px-4 h-12 border-b border-default bg-rui-grey-50 dark:bg-dark-elevated/[0.9] sticky top-0">
    <!-- Left side: Column headers -->
    <div class="flex items-center text-sm text-rui-text-secondary font-medium">
      <span>{{ t('transactions.events.headers.event_identifier') }}</span>
    </div>

    <!-- Right side: Sort + Pagination -->
    <div class="flex items-center gap-3">
      <!-- Sort by timestamp -->
      <RuiButton
        variant="text"
        size="sm"
        class="text-sm"
        @click="toggleSort()"
      >
        {{ t('common.datetime') }}
        <template #append>
          <RuiIcon
            :name="sortDirection === 'asc' ? 'lu-arrow-up' : 'lu-arrow-down'"
            size="14"
            :class="{ 'opacity-50': sortColumn !== 'timestamp' }"
          />
        </template>
      </RuiButton>

      <RuiDivider
        vertical
        class="h-4"
      />

      <!-- Items per page -->
      <div class="flex items-center gap-2">
        <span class="text-sm text-rui-text-secondary">{{ t('data_table.rows_per_page') }}</span>
        <RuiMenuSelect
          v-model="itemsPerPage"
          :options="limits"
          dense
          hide-details
          class="w-20"
        />
      </div>

      <RuiDivider
        vertical
        class="h-4"
      />

      <!-- Pagination info -->
      <span class="text-sm text-rui-text-secondary whitespace-nowrap">
        {{ (currentPage - 1) * itemsPerPage + 1 }}-{{ Math.min(currentPage * itemsPerPage, pagination.total) }}
        {{ t('common.of') }}
        {{ pagination.total }}
      </span>

      <!-- Pagination buttons -->
      <div class="flex items-center">
        <RuiButton
          variant="text"
          icon
          size="sm"
          :disabled="currentPage <= 1"
          @click="currentPage = currentPage - 1"
        >
          <RuiIcon
            name="lu-chevron-left"
            size="18"
          />
        </RuiButton>
        <RuiButton
          variant="text"
          icon
          size="sm"
          :disabled="currentPage >= totalPages"
          @click="currentPage = currentPage + 1"
        >
          <RuiIcon
            name="lu-chevron-right"
            size="18"
          />
        </RuiButton>
      </div>
    </div>
  </div>
</template>
