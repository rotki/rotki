<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import { isEqual } from 'es-toolkit';
import DateDisplay from '@/components/display/DateDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { type CustomizedEventDuplicate, type DuplicateRow, useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import HashLink from '@/modules/common/links/HashLink.vue';

const selected = defineModel<string[]>('selected', { default: () => [] });

const props = defineProps<{
  groupIds: string[];
  emptyDescription: string;
  selectable?: boolean;
  fixLoading?: boolean;
}>();

defineEmits<{
  fix: [duplicate: CustomizedEventDuplicate];
}>();

const DEFAULT_LIMIT = 10;

const { groupIds, selectable } = toRefs(props);

const { fetchDuplicateEvents } = useCustomizedEventDuplicates();

const { t } = useI18n({ useScope: 'global' });

const rows = ref<DuplicateRow[]>([]);
const total = ref<number>(0);
const loading = ref<boolean>(false);
const pagination = ref<TablePaginationData>({
  limit: DEFAULT_LIMIT,
  page: 1,
  total: 0,
});

const columns = computed<DataTableColumn<DuplicateRow>[]>(() => {
  const cols: DataTableColumn<DuplicateRow>[] = [
    {
      key: 'timestamp',
      label: t('common.datetime'),
    },
    {
      align: 'center',
      key: 'location',
      label: t('common.location'),
    },
    {
      key: 'txHash',
      label: t('common.tx_hash'),
    },
  ];

  if (get(selectable)) {
    cols.push({
      key: 'actions',
      label: '',
    });
  }

  return cols;
});

async function fetchData(): Promise<void> {
  const ids = get(groupIds);
  if (ids.length === 0) {
    set(rows, []);
    set(total, 0);
    set(pagination, { ...get(pagination), total: 0 });
    return;
  }

  set(loading, true);
  try {
    const { limit, page } = get(pagination);
    const offset = (page - 1) * limit;

    const result = await fetchDuplicateEvents({
      groupIds: ids,
      limit,
      offset,
    });

    set(rows, result.data);
    set(total, result.total);
    set(pagination, { ...get(pagination), total: result.total });
  }
  finally {
    set(loading, false);
  }
}

function onPaginationChange(newPagination: TablePaginationData): void {
  set(pagination, newPagination);
}

watch(groupIds, async () => {
  // Reset to first page when group IDs change
  set(pagination, { ...get(pagination), page: 1 });
  await fetchData();
});

watchImmediate(pagination, async (curr, prev) => {
  if (isEqual(curr, prev)) {
    return;
  }
  await fetchData();
});
</script>

<template>
  <RuiDataTable
    v-model="selected"
    v-model:pagination.external="pagination"
    :cols="columns"
    :rows="rows"
    row-attr="groupIdentifier"
    outlined
    dense
    :multi-page-select="selectable"
    :loading="loading"
    class="table-inside-dialog max-h-[calc(100vh-23rem)]"
    :empty="{ description: emptyDescription }"
    @update:pagination="onPaginationChange($event)"
  >
    <template #item.txHash="{ row }">
      <HashLink
        type="transaction"
        :text="row.txHash"
        :location="row.location"
      />
    </template>
    <template #item.location="{ row }">
      <LocationDisplay :identifier="row.location" />
    </template>
    <template #item.timestamp="{ row }">
      <DateDisplay
        :timestamp="row.timestamp"
        milliseconds
      />
    </template>
    <template
      v-if="selectable"
      #item.actions="{ row }"
    >
      <div class="flex justify-end">
        <RuiButton
          size="sm"
          color="primary"
          :loading="fixLoading"
          @click="$emit('fix', row.original)"
        >
          <template #prepend>
            <RuiIcon
              name="lu-wand-sparkles"
              size="16"
            />
          </template>
          {{ t('customized_event_duplicates.actions.fix') }}
        </RuiButton>
      </div>
    </template>
  </RuiDataTable>
</template>
