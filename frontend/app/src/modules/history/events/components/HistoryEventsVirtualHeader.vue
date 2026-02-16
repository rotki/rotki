<script setup lang="ts">
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { type DataTableSortData, type TablePaginationData, useBreakpoint } from '@rotki/ui-library';

const sort = defineModel<DataTableSortData<HistoryEventEntry>>('sort', { required: true });
const pagination = defineModel<TablePaginationData>('pagination', { required: true });

defineProps<{
  loading?: boolean;
  total: number;
  found: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const { isSmAndDown } = useBreakpoint();

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
  <div class="relative flex items-center justify-between gap-2 md:gap-4 px-3 md:px-4 h-10 lg:h-12 border-b border-default bg-white dark:bg-dark-elevated/[0.9] sticky top-0 z-5">
    <RuiProgress
      v-if="loading"
      class="!absolute -bottom-0.5 left-0 w-full pointer-events-none"
      color="primary"
      variant="indeterminate"
      thickness="2"
    />
    <!-- Left side: Column headers - hidden on mobile -->
    <div class="hidden md:flex items-center text-sm text-rui-text-secondary font-medium">
      <span>{{ t('transactions.events.headers.event_identifier') }}</span>
    </div>

    <!-- Right side: Sort + Pagination -->
    <div class="flex items-center gap-2 md:gap-3 flex-1 md:flex-initial justify-between md:justify-end">
      <!-- Sort by timestamp -->
      <RuiButton
        variant="text"
        size="sm"
        class="text-sm"
        @click="toggleSort()"
      >
        <span class="hidden sm:inline">{{ t('common.datetime') }}</span>
        <RuiIcon
          class="sm:hidden"
          name="lu-calendar"
          size="16"
        />
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
      <div class="flex items-center gap-1 md:gap-2">
        <span class="hidden lg:inline text-xs text-rui-text-secondary whitespace-nowrap">{{ t('data_table.rows_per_page') }}</span>
        <RuiIcon
          class="lg:hidden text-rui-text-secondary"
          name="lu-rows-3"
          size="16"
        />
        <RuiMenuSelect
          v-model="itemsPerPage"
          :options="limits"
          dense
          hide-details
          label-class="!text-xs"
          class="w-18"
        />
      </div>

      <RuiDivider
        vertical
        class="h-4 hidden sm:block"
      />

      <!-- Pagination info - hidden on small screens -->
      <span
        v-if="!isSmAndDown"
        class="text-sm text-rui-text-secondary whitespace-nowrap"
      >
        {{ ((currentPage - 1) * itemsPerPage + 1).toLocaleString() }}-{{ Math.min(currentPage * itemsPerPage, pagination.total).toLocaleString() }}
        {{ t('common.of') }}
        {{ pagination.total.toLocaleString() }}
      </span>

      <!-- Pagination buttons -->
      <div class="flex items-center">
        <RuiButton
          variant="text"
          icon
          size="sm"
          :disabled="currentPage <= 1"
          @click="currentPage = 1"
        >
          <RuiIcon
            name="lu-chevrons-left"
            size="18"
          />
        </RuiButton>
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
        <RuiButton
          variant="text"
          icon
          size="sm"
          :disabled="currentPage >= totalPages"
          @click="currentPage = totalPages"
        >
          <RuiIcon
            name="lu-chevrons-right"
            size="18"
          />
        </RuiButton>
      </div>
    </div>
  </div>
</template>
