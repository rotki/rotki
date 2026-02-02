<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type {
  PotentialMatchRow,
  UnmatchedAssetMovement,
} from '@/composables/history/events/use-unmatched-asset-movements';
import type {
  HistoryEventCollectionRow,
  HistoryEventEntry,
  HistoryEventEntryWithMeta,
} from '@/types/history/events/schemas';
import SimpleTable from '@/components/common/SimpleTable.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import HashLink from '@/modules/common/links/HashLink.vue';

const selectedMatchId = defineModel<number | undefined>('selectedMatchId', { required: true });

const searchTimeRange = defineModel<string>('searchTimeRange', { required: true });

const onlyExpectedAssets = defineModel<boolean>('onlyExpectedAssets', { required: true });

const tolerancePercentage = defineModel<string>('tolerancePercentage', { required: true });

const props = defineProps<{
  movement: UnmatchedAssetMovement;
  matches: PotentialMatchRow[];
  loading: boolean;
}>();

const emit = defineEmits<{
  search: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

const columns = computed<DataTableColumn<PotentialMatchRow>[]>(() => [
  {
    key: 'timestamp',
    label: t('common.datetime'),
  },
  {
    class: 'whitespace-pre-line',
    key: 'txRef',
    label: `${t('common.tx_hash')} -\n${t('common.account')}`,
  },
  {
    class: 'whitespace-pre-line',
    key: 'eventTypeAndSubtype',
    label: `${t('transactions.events.form.event_type.label')} -\n${t('transactions.events.form.event_subtype.label')}`,
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

function isSelected(row: PotentialMatchRow): boolean {
  return get(selectedMatchId) === row.entry.identifier;
}

const movementEntry = computed<HistoryEventEntry>(() => {
  const { entry, ...meta } = getEventEntry(props.movement.events);
  return { ...entry, ...meta };
});

watchDebounced(onlyExpectedAssets, () => {
  emit('search');
}, { debounce: 200 });
</script>

<template>
  <div>
    <div class="mb-4">
      <p class="text-body-2 font-medium mb-2">
        {{ t('asset_movement_matching.dialog.matching_for') }}
      </p>
      <SimpleTable>
        <thead>
          <tr>
            <th>{{ t('common.datetime') }}</th>
            <th class="!text-center">
              {{ t('common.exchange') }}
            </th>
            <th>{{ t('common.type') }}</th>
            <th>{{ t('common.asset') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <DateDisplay
                :timestamp="movementEntry.timestamp"
                milliseconds
              />
            </td>
            <td class="text-center">
              <LocationDisplay :identifier="movementEntry.location" />
            </td>
            <td>
              <BadgeDisplay>
                {{ movementEntry.eventType }}
              </BadgeDisplay>
            </td>
            <td>
              <HistoryEventAsset :event="movementEntry" />
            </td>
          </tr>
        </tbody>
      </SimpleTable>
    </div>
    <div class="border-t border-default pt-4">
      <div class="text-body-2 font-medium mb-4">
        {{ t('asset_movement_matching.dialog.search_description') }}
      </div>
      <div class="flex items-center gap-4 mb-4 flex-wrap">
        <RuiTextField
          v-model="searchTimeRange"
          type="number"
          min="1"
          color="primary"
          hide-details
          max="168"
          :label="t('asset_movement_matching.dialog.time_range_hours')"
          class="w-40"
          variant="outlined"
          dense
        />
        <AmountInput
          v-model="tolerancePercentage"
          type="number"
          step="0.001"
          variant="outlined"
          hide-details
          dense
          :label="t('asset_movement_matching.settings.amount_tolerance.label')"
          class="w-40"
        />
        <RuiTooltip
          :popper="{ placement: 'top' }"
          tooltip-class="max-w-80"
        >
          <template #activator>
            <RuiCheckbox
              v-model="onlyExpectedAssets"
              color="primary"
              hide-details
              size="sm"
            >
              {{ t('asset_movement_matching.dialog.only_expected_assets') }}
            </RuiCheckbox>
          </template>
          {{ t('asset_movement_matching.dialog.only_expected_assets_hint') }}
        </RuiTooltip>
        <RuiButton
          class="!h-10"
          :loading="loading"
          @click="emit('search')"
        >
          {{ t('common.actions.search') }}
        </RuiButton>
      </div>
    </div>

    <RuiDataTable
      :cols="columns"
      :rows="matches"
      row-attr="identifier"
      class="table-inside-dialog !max-h-[calc(100vh-33rem)]"
      dense
      outlined
      :empty="{ label: t('asset_movement_matching.dialog.no_matches_found') }"
      :loading="loading"
    >
      <template #item.txRef="{ row }">
        <div class="flex items-center gap-1.5">
          <LocationIcon
            horizontal
            icon
            size="1.25rem"
            :item="row.entry.location"
          />
          <HashLink
            v-if="'txRef' in row.entry && row.entry.txRef"
            :text="row.entry.txRef"
            type="transaction"
            :location="row.entry.location"
          />
          <span v-else>-</span>
        </div>
        <div class="pt-1">
          <HashLink
            v-if="row.entry.locationLabel"
            :text="row.entry.locationLabel"
            :location="row.entry.location"
          />
          <span v-else>-</span>
        </div>
      </template>
      <template #item.asset="{ row }">
        <HistoryEventAsset :event="row.entry" />
      </template>
      <template #item.eventTypeAndSubtype="{ row }">
        <div>{{ getHistoryEventTypeName(row.entry.eventType) }} -</div>
        <div>{{ getHistoryEventSubTypeName(row.entry.eventSubtype) }}</div>
      </template>
      <template #item.timestamp="{ row }">
        <DateDisplay
          :timestamp="row.entry.timestamp"
          milliseconds
        />
      </template>
      <template #item.actions="{ row }">
        <div class="flex items-center justify-end gap-4">
          <RuiTooltip
            v-if="row.isCloseMatch"
            :open-delay="200"
          >
            <template #activator>
              <RuiIcon
                name="lu-thumbs-up"
                size="16"
                color="success"
              />
            </template>
            {{ t('asset_movement_matching.dialog.recommended') }}
          </RuiTooltip>
          <RuiButton
            size="sm"
            :color="isSelected(row) ? 'success' : 'primary'"
            :variant="isSelected(row) ? 'default' : 'outlined'"
            class="min-w-24"
            @click="selectedMatchId = row.entry.identifier"
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
  </div>
</template>
