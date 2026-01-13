<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { HistoryEventCollectionRow, HistoryEventEntryWithMeta } from '@/types/history/events/schemas';
import PotentialMatchesList from '@/components/history/events/PotentialMatchesList.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import {
  type UnmatchedAssetMovement,
  useUnmatchedAssetMovements,
} from '@/composables/history/events/use-unmatched-asset-movements';

export interface PotentialMatchRow {
  identifier: number;
  asset: string;
  amount: BigNumber;
  location: string;
  locationLabel?: string;
  timestamp: number;
  txRef?: string;
  eventType: string;
  eventSubtype: string;
  isCloseMatch: boolean;
}

const modelValue = defineModel<boolean>({ required: true });

const props = defineProps<{
  movement: UnmatchedAssetMovement;
}>();

const emit = defineEmits<{
  matched: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  matchAssetMovement,
  refreshUnmatchedAssetMovements,
} = useUnmatchedAssetMovements();

const { fetchHistoryEvents, getAssetMovementMatches } = useHistoryEventsApi();

const DEFAULT_HOUR_RANGE = 4;

const searchLoading = ref<boolean>(false);
const matchingLoading = ref<boolean>(false);
const potentialMatches = ref<PotentialMatchRow[]>([]);
const selectedMatchId = ref<number>();
const searchTimeRange = ref<string>(DEFAULT_HOUR_RANGE.toString());
const onlyExpectedAssets = ref<boolean>(true);

function getEventEntry(row: HistoryEventCollectionRow): HistoryEventEntryWithMeta {
  const events = Array.isArray(row) ? row : [row];
  return events[0];
}

function transformToMatchRow(row: HistoryEventCollectionRow, isCloseMatch: boolean): PotentialMatchRow {
  const eventData = getEventEntry(row);
  const entry = eventData.entry;

  return {
    amount: entry.amount,
    asset: entry.asset,
    eventSubtype: entry.eventSubtype,
    eventType: entry.eventType,
    identifier: entry.identifier,
    isCloseMatch,
    location: entry.location,
    locationLabel: entry.locationLabel ?? undefined,
    timestamp: entry.timestamp,
    txRef: 'txRef' in entry ? entry.txRef : undefined,
  };
}

async function searchPotentialMatches(): Promise<void> {
  set(searchLoading, true);
  set(potentialMatches, []);

  try {
    const groupIdentifier = props.movement.groupIdentifier;

    const hours = Number.parseInt(get(searchTimeRange), 10) || DEFAULT_HOUR_RANGE;
    const timeRangeInSeconds = hours * 60 * 60;

    // Get match suggestions from backend
    const suggestions = await getAssetMovementMatches(groupIdentifier, timeRangeInSeconds, get(onlyExpectedAssets));
    const allIdentifiers = [...suggestions.closeMatches, ...suggestions.otherEvents];

    if (allIdentifiers.length === 0) {
      set(potentialMatches, []);
      return;
    }

    // Fetch the actual events using the identifiers
    const response = await fetchHistoryEvents({
      aggregateByGroupIds: false,
      identifiers: allIdentifiers.map(String),
      limit: -1,
      offset: 0,
    });

    // Transform and mark close matches
    const closeMatchSet = new Set(suggestions.closeMatches);
    const matches = response.entries
      .map(row => transformToMatchRow(row, closeMatchSet.has(getEventEntry(row).entry.identifier)));

    // Reorder matches to follow the order of allIdentifiers from backend
    const identifierOrderMap = new Map(allIdentifiers.map((id, index) => [id, index]));
    matches.sort((a, b) => {
      const orderA = identifierOrderMap.get(a.identifier) ?? Number.MAX_SAFE_INTEGER;
      const orderB = identifierOrderMap.get(b.identifier) ?? Number.MAX_SAFE_INTEGER;
      return orderA - orderB;
    });

    set(potentialMatches, matches);
  }
  catch (error) {
    console.error('Failed to search potential matches:', error);
  }
  finally {
    set(searchLoading, false);
  }
}

async function confirmMatch(): Promise<void> {
  const matchId = get(selectedMatchId);

  if (!matchId)
    return;

  set(matchingLoading, true);

  try {
    const eventEntry = getEventEntry(props.movement.events);
    const assetMovementId = eventEntry.entry.identifier;

    if (!assetMovementId)
      return;

    const result = await matchAssetMovement(assetMovementId, matchId);

    if (result.success) {
      await refreshUnmatchedAssetMovements(true);
      set(modelValue, false);
      emit('matched');
    }
  }
  finally {
    set(matchingLoading, false);
  }
}

function closeDialog(): void {
  set(modelValue, false);
}

watch(modelValue, async (isOpen) => {
  if (isOpen) {
    set(potentialMatches, []);
    set(selectedMatchId, undefined);
    set(searchTimeRange, DEFAULT_HOUR_RANGE.toString());
    set(onlyExpectedAssets, true);
    await searchPotentialMatches();
  }
}, { immediate: true });
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="1000"
  >
    <RuiCard content-class="max-h-[calc(100vh-250px)]">
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 pt-2">
          <CardTitle>
            {{ t('asset_movement_matching.dialog.select_match_title') }}
          </CardTitle>
          <RuiButton
            variant="text"
            icon
            @click="closeDialog()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </template>

      <PotentialMatchesList
        v-model:selected-match-id="selectedMatchId"
        v-model:search-time-range="searchTimeRange"
        v-model:only-expected-assets="onlyExpectedAssets"
        :movement="movement"
        :matches="potentialMatches"
        :loading="searchLoading"
        @search="searchPotentialMatches()"
      />

      <template #footer>
        <div class="w-full flex justify-end gap-2">
          <RuiButton
            variant="text"
            @click="closeDialog()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="!selectedMatchId"
            :loading="matchingLoading"
            @click="confirmMatch()"
          >
            {{ t('asset_movement_matching.dialog.confirm_match') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
