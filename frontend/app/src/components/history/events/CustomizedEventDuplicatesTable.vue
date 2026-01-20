<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { CustomizedEventDuplicate, DuplicateRow } from '@/composables/history/events/use-customized-event-duplicates';
import DateDisplay from '@/components/display/DateDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import HashLink from '@/modules/common/links/HashLink.vue';

const selected = defineModel<string[]>('selected', { default: () => [] });

const props = defineProps<{
  rows: DuplicateRow[];
  loading: boolean;
  emptyDescription: string;
  selectable?: boolean;
  fixLoading?: boolean;
}>();

defineEmits<{
  fix: [duplicate: CustomizedEventDuplicate];
}>();

const { selectable } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

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
</script>

<template>
  <RuiDataTable
    v-model="selected"
    :cols="columns"
    :rows="rows"
    row-attr="groupIdentifier"
    outlined
    dense
    :multi-page-select="selectable"
    :loading="loading"
    class="table-inside-dialog max-h-[calc(100vh-23rem)]"
    :empty="{ description: emptyDescription }"
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
