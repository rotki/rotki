<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import type { UnmatchedAssetMovement } from '@/composables/history/events/use-unmatched-asset-movements';
import type { HistoryEventCollectionRow, HistoryEventEntryWithMeta } from '@/types/history/events/schemas';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { ValueDisplay } from '@/modules/amount-display/components';

interface UnmatchedMovementRow {
  groupIdentifier: string;
  asset: string;
  amount: BigNumber;
  eventType: string;
  isFiat: boolean;
  location: string;
  timestamp: number;
  original: UnmatchedAssetMovement;
}

const selected = defineModel<string[]>('selected', { required: true });

const props = defineProps<{
  movements: UnmatchedAssetMovement[];
  ignoreLoading?: boolean;
  showRestore?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  ignore: [movement: UnmatchedAssetMovement];
  restore: [movement: UnmatchedAssetMovement];
  select: [movement: UnmatchedAssetMovement];
}>();

const { t } = useI18n({ useScope: 'global' });

const columns = computed<DataTableColumn<UnmatchedMovementRow>[]>(() => [
  {
    key: 'timestamp',
    label: t('common.datetime'),
  },
  {
    align: 'center',
    key: 'location',
    label: t('common.exchange'),
  },
  {
    key: 'eventType',
    label: t('common.type'),
  },
  {
    align: 'end',
    key: 'amount',
    label: t('common.amount'),
  },
  {
    key: 'asset',
    label: t('common.asset'),
  },
  {
    key: 'actions',
    label: '',
  },
]);

function getEventEntry(row: HistoryEventCollectionRow): HistoryEventEntryWithMeta {
  return Array.isArray(row) ? row[0] : row;
}

const rows = computed<UnmatchedMovementRow[]>(() =>
  props.movements.map((movement) => {
    const entry = getEventEntry(movement.events).entry;
    return {
      amount: entry.amount,
      asset: entry.asset,
      eventType: entry.eventType,
      groupIdentifier: movement.groupIdentifier,
      isFiat: movement.isFiat,
      location: entry.location,
      original: movement,
      timestamp: entry.timestamp,
    };
  }),
);

const emptyDescription = computed<string>(() =>
  props.showRestore
    ? t('asset_movement_matching.dialog.no_ignored')
    : t('asset_movement_matching.dialog.no_unmatched'),
);
</script>

<template>
  <div>
    <p
      v-if="!showRestore"
      class="text-body-2 text-rui-text-secondary mb-4"
    >
      {{ t('asset_movement_matching.dialog.description') }}
    </p>

    <RuiDataTable
      v-model="selected"
      :cols="columns"
      :rows="rows"
      row-attr="groupIdentifier"
      outlined
      dense
      multi-page-select
      :loading="loading"
      class="table-inside-dialog max-h-[calc(100vh-23rem)]"
      :empty="{ description: emptyDescription }"
    >
      <template #item.asset="{ row }">
        <div class="flex items-center gap-2">
          <AssetDetails :asset="row.asset" />
          <RuiTooltip
            v-if="row.isFiat"
            :open-delay="400"
            :popper="{ placement: 'top' }"
            tooltip-class="max-w-80"
          >
            <template #activator>
              <RuiChip
                size="sm"
                color="warning"
              >
                {{ t('asset_movement_matching.fiat_hint.label') }}
              </RuiChip>
            </template>
            {{ t('asset_movement_matching.fiat_hint.tooltip') }}
          </RuiTooltip>
        </div>
      </template>
      <template #item.amount="{ row }">
        <ValueDisplay :value="row.amount" />
      </template>
      <template #item.eventType="{ row }">
        <BadgeDisplay>
          {{ row.eventType }}
        </BadgeDisplay>
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
      <template #item.actions="{ row }">
        <div class="flex gap-2">
          <template v-if="showRestore">
            <RuiTooltip
              :open-delay="400"
              :popper="{ placement: 'top' }"
            >
              <template #activator>
                <RuiButton
                  size="sm"
                  color="primary"
                  :loading="ignoreLoading"
                  @click="emit('restore', row.original)"
                >
                  {{ t('asset_movement_matching.dialog.restore') }}
                </RuiButton>
              </template>
              {{ t('asset_movement_matching.dialog.restore_tooltip') }}
            </RuiTooltip>
          </template>
          <template v-else>
            <RuiButton
              size="sm"
              color="primary"
              @click="emit('select', row.original)"
            >
              {{ t('asset_movement_matching.dialog.find_match') }}
            </RuiButton>
            <RuiTooltip
              :open-delay="400"
              :popper="{ placement: 'top' }"
            >
              <template #activator>
                <RuiButton
                  size="sm"
                  variant="outlined"
                  :loading="ignoreLoading"
                  @click="emit('ignore', row.original)"
                >
                  {{ t('asset_movement_matching.dialog.ignore') }}
                </RuiButton>
              </template>
              {{ t('asset_movement_matching.dialog.ignore_tooltip') }}
            </RuiTooltip>
          </template>
        </div>
      </template>
    </RuiDataTable>
  </div>
</template>
