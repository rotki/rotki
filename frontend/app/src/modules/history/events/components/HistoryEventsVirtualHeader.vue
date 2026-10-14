<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { type DataTableSortData, type TablePaginationData, useBreakpoint } from '@rotki/ui-library';
import {
  leadingSortColumn,
  pageCount,
  sortDirection as sortDirectionOf,
  toggledSort,
} from '@/modules/history/events/components/history-events-table-header';
import { injectHistoryEventsSelection } from '@/modules/history/events/use-history-events-selection-context';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';

const sort = defineModel<DataTableSortData<HistoryEventEntry>>('sort', { required: true });
const pagination = defineModel<TablePaginationData>('pagination', { required: true });

defineProps<{
  loading?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const selection = injectHistoryEventsSelection();

const globalItemsPerPage = useItemsPerPage();
const { isSmAndDown } = useBreakpoint();

/** Selection mode widens the rows' gutter for their checkboxes, so the column labels move with them. */
const selecting = computed<boolean>(() => !!selection && get(selection.isSelectionMode));

const sortColumn = computed<'timestamp' | undefined>(() => leadingSortColumn(get(sort), 'timestamp'));

const sortDirection = computed<'asc' | 'desc'>(() => sortDirectionOf(get(sort)));

function toggleSort(): void {
  set(sort, toggledSort(get(sort), 'timestamp'));
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

    set(globalItemsPerPage, limit);
  },
});

const totalPages = computed<number>(() => pageCount(get(pagination).total, get(itemsPerPage)));

const limits = [10, 25, 50, 100];
</script>

<template>
  <div class="relative flex items-center justify-between gap-2 md:gap-4 px-3 md:px-4 h-10 border-b border-rui-divider bg-rui-surface-muted sticky top-0 z-5">
    <RuiProgress
      v-if="loading"
      class="absolute! -bottom-0.5 left-0 w-full pointer-events-none"
      color="primary"
      variant="indeterminate"
      thickness="2"
    />
    <div
      class="hidden lg:flex items-center gap-4 min-w-0 flex-1 text-[0.8125rem] leading-5 text-rui-text-secondary font-medium"
      :class="selecting ? 'pl-12' : 'pl-2'"
    >
      <span class="w-56 shrink-0">{{ t('common.type') }}</span>
      <span class="w-56 xl:w-60 shrink-0">{{ t('common.asset') }}</span>
      <span class="hidden xl:inline truncate">{{ t('common.description') }}</span>
    </div>

    <div class="flex items-center gap-2 md:gap-3 flex-1 lg:flex-initial justify-between md:justify-end">
      <button
        type="button"
        class="group/sort inline-flex items-center gap-1 rounded-rui-control px-1.5 py-1 text-[0.8125rem] leading-5 font-medium transition-colors focus-visible:outline-2 focus-visible:outline-rui-primary"
        :class="sortColumn === 'timestamp' ? 'text-rui-text' : 'text-rui-text-secondary'"
        :aria-label="t('common.datetime')"
        data-testid="events-sort-date"
        @click="toggleSort()"
      >
        <span class="hidden sm:inline">{{ t('common.datetime') }}</span>
        <RuiIcon
          class="sm:hidden"
          name="lu-calendar"
          size="16"
        />
        <RuiIcon
          :name="sortDirection === 'asc' ? 'lu-arrow-up' : 'lu-arrow-down'"
          size="14"
          class="transition"
          :class="{ 'opacity-30 group-hover/sort:opacity-60': sortColumn !== 'timestamp' }"
        />
      </button>

      <RuiDivider
        vertical
        class="h-4"
      />

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
          :label="t('data_table.rows_per_page')"
          label-placement="hidden"
          dense
          hide-details
          :class-names="{ label: 'text-xs!' }"
          class="w-18"
        />
      </div>

      <RuiDivider
        vertical
        class="h-4 hidden sm:block"
      />

      <span
        v-if="!isSmAndDown"
        class="text-[0.8125rem] leading-5 text-rui-text-secondary whitespace-nowrap"
        data-testid="events-page-range"
      >
        {{ ((currentPage - 1) * itemsPerPage + 1).toLocaleString() }}-{{ Math.min(currentPage * itemsPerPage, pagination.total).toLocaleString() }}
        {{ t('common.of') }}
        {{ pagination.total.toLocaleString() }}
      </span>

      <div class="flex items-center">
        <RuiButton
          variant="text"
          icon
          size="sm"
          :disabled="currentPage <= 1"
          :aria-label="t('data_table.first_page')"
          data-testid="events-page-first"
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
          :aria-label="t('data_table.previous_page')"
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
          :aria-label="t('data_table.next_page')"
          data-testid="events-page-next"
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
          :aria-label="t('data_table.last_page')"
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
