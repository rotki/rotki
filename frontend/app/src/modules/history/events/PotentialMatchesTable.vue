<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { PotentialMatchRow } from '@/modules/history/events/matching/types';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import RecommendedMatchIcon from '@/modules/history/events/RecommendedMatchIcon.vue';
import ShowInEventsButton from '@/modules/history/events/ShowInEventsButton.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const selectedIds = defineModel<number[]>('selectedIds', { required: true });

const { matches, highlightedIdentifier, loading, maxHeight } = defineProps<{
  matches: PotentialMatchRow[];
  highlightedIdentifier?: number;
  loading?: boolean;
  maxHeight: string;
  emptyLabel: string;
}>();

const emit = defineEmits<{
  'show-in-events': [data: { identifier: number; groupIdentifier: string }];
}>();

const { t } = useI18n({ useScope: 'global' });

const { getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

const columns = computed<DataTableColumn<PotentialMatchRow>[]>(() => [
  { key: 'timestamp', label: t('common.datetime') },
  { class: 'min-w-32', key: 'eventTypeAndSubtype', label: t('asset_movement_matching.dialog.event_column') },
  { class: 'min-w-32', key: 'txRef', label: t('asset_movement_matching.dialog.transaction_column') },
  { key: 'asset', label: t('common.asset') },
  { key: 'actions', label: '' },
]);

function isSelected(row: PotentialMatchRow): boolean {
  return get(selectedIds).includes(row.entry.identifier);
}

function toggle(row: PotentialMatchRow): void {
  const identifier = row.entry.identifier;
  const ids = get(selectedIds);
  set(selectedIds, ids.includes(identifier) ? ids.filter(id => id !== identifier) : [...ids, identifier]);
}

function getRowClass(row: PotentialMatchRow): string {
  return row.entry.identifier === highlightedIdentifier ? '!bg-rui-success/15' : '';
}
</script>

<template>
  <ScrollableDialogContent :max-height="maxHeight">
    <RuiDataTable
      :cols="columns"
      :rows="matches"
      row-attr="identifier"
      :item-class="getRowClass"
      dense
      outlined
      hide-default-header
      :empty="{ label: emptyLabel }"
      :loading="loading"
    >
      <template #item.timestamp="{ row }">
        <DateDisplay
          :timestamp="row.entry.timestamp"
          milliseconds
        />
      </template>
      <template #item.eventTypeAndSubtype="{ row }">
        <div>{{ getHistoryEventTypeName(row.entry.eventType) }} -</div>
        <div>{{ getHistoryEventSubTypeName(row.entry.eventSubtype) }}</div>
      </template>
      <template #item.txRef="{ row }">
        <div
          v-if="'txRef' in row.entry && row.entry.txRef"
          class="flex items-center gap-1"
        >
          <LocationIcon
            horizontal
            icon
            size="1.25rem"
            :item="row.entry.location"
          />
          <HashLink
            :text="row.entry.txRef"
            type="transaction"
            :location="row.entry.location"
          />
        </div>
        <div>
          <span v-if="!row.entry.locationLabel">-</span>
          <HistoryEventAccount
            v-else
            :location="row.entry.location"
            :location-label="row.entry.locationLabel"
          />
        </div>
      </template>
      <template #item.asset="{ row }">
        <div class="flex items-center gap-2">
          <HistoryEventAsset
            disable-options
            :event="row.entry"
          />
        </div>
      </template>
      <template #item.actions="{ row }">
        <div class="flex items-center justify-end gap-2">
          <RecommendedMatchIcon v-if="row.isCloseMatch" />
          <ShowInEventsButton
            @click="emit('show-in-events', { groupIdentifier: row.entry.groupIdentifier, identifier: row.entry.identifier })"
          />
          <RuiButton
            size="sm"
            :color="isSelected(row) ? 'success' : 'primary'"
            :variant="isSelected(row) ? 'default' : 'outlined'"
            class="min-w-24"
            data-testid="potential-match-select"
            :data-key="row.entry.identifier"
            @click="toggle(row)"
          >
            <template
              v-if="isSelected(row)"
              #prepend
            >
              <RuiIcon
                name="lu-check"
                size="12"
              />
            </template>
            {{ isSelected(row)
              ? t('asset_movement_matching.dialog.selected')
              : t('asset_movement_matching.dialog.select')
            }}
          </RuiButton>
        </div>
      </template>
    </RuiDataTable>
  </ScrollableDialogContent>
</template>
