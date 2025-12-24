<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import type { UnmatchedAssetMovement } from '@/composables/history/events/use-unmatched-asset-movements';
import type { HistoryEventCollectionRow, HistoryEventEntryWithMeta } from '@/types/history/events/schemas';
import SimpleTable from '@/components/common/SimpleTable.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import HashLink from '@/modules/common/links/HashLink.vue';

interface PotentialMatchRow {
  identifier: number;
  asset: string;
  amount: BigNumber;
  location: string;
  timestamp: number;
  txRef: string;
}

const selectedMatchId = defineModel<number | undefined>('selectedMatchId', { required: true });

const searchTimeRange = defineModel<string>('searchTimeRange', { required: true });

const props = defineProps<{
  movement: UnmatchedAssetMovement;
  matches: PotentialMatchRow[];
  loading: boolean;
}>();

const emit = defineEmits<{
  search: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const columns = computed<DataTableColumn<PotentialMatchRow>[]>(() => [
  {
    key: 'timestamp',
    label: t('common.datetime'),
  },
  {
    key: 'txRef',
    label: t('common.tx_hash'),
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
  const events = Array.isArray(row) ? row : [row];
  return events[0];
}

const movementEntry = computed(() => getEventEntry(props.movement.events).entry);
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
            <th class="!text-end">
              {{ t('common.amount') }}
            </th>
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
            <td class="text-end">
              <AmountDisplay :value="movementEntry.amount" />
            </td>
            <td>
              <AssetDetails :asset="movementEntry.asset" />
            </td>
          </tr>
        </tbody>
      </SimpleTable>
    </div>

    <div class="flex items-center gap-2 mb-4">
      <p class="text-body-2 font-medium mr-4">
        {{ t('asset_movement_matching.dialog.search_description') }}
      </p>
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
      <RuiButton
        class="!h-10"
        :loading="loading"
        @click="emit('search')"
      >
        {{ t('common.actions.search') }}
      </RuiButton>
    </div>

    <RuiDataTable
      :cols="columns"
      :rows="matches"
      row-attr="identifier"
      class="table-inside-dialog !max-h-[calc(100vh-32rem)]"
      dense
      outlined
      :empty="{ label: t('asset_movement_matching.dialog.no_matches_found') }"
      :loading="loading"
    >
      <template #item.txRef="{ row }">
        <div class="flex items-center gap-3">
          <LocationIcon
            horizontal
            icon
            size="1.5rem"
            :item="row.location"
          />
          <HashLink
            :text="row.txRef"
            type="transaction"
            :location="row.location"
          />
        </div>
      </template>
      <template #item.asset="{ row }">
        <AssetDetails :asset="row.asset" />
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>
      <template #item.timestamp="{ row }">
        <DateDisplay
          :timestamp="row.timestamp"
          milliseconds
        />
      </template>
      <template #item.actions="{ row }">
        <RuiButton
          size="sm"
          :color="selectedMatchId === row.identifier ? 'success' : 'primary'"
          :variant="selectedMatchId === row.identifier ? 'default' : 'outlined'"
          @click="selectedMatchId = row.identifier"
        >
          <template
            v-if="selectedMatchId === row.identifier"
            #prepend
          >
            <RuiIcon
              name="lu-check"
              size="12"
            />
          </template>
          {{ selectedMatchId === row.identifier
            ? t('asset_movement_matching.dialog.selected')
            : t('asset_movement_matching.dialog.select')
          }}
        </RuiButton>
      </template>
    </RuiDataTable>
  </div>
</template>
