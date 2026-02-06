<script setup lang="ts">
import type { HistoryEventCollectionRow } from '@/types/history/events/schemas';
import { bigNumberify } from '@rotki/common';
import PotentialMatchesList from '@/components/history/events/PotentialMatchesList.vue';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useAssetMovementMatchingApi } from '@/composables/api/history/events/asset-movement-matching';
import {
  type PotentialMatchRow,
  type UnmatchedAssetMovement,
  useUnmatchedAssetMovements,
} from '@/composables/history/events/use-unmatched-asset-movements';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { getEventEntryFromCollection } from '@/utils/history/events';
import { logger } from '@/utils/logging';

const props = defineProps<{
  movement: UnmatchedAssetMovement;
  isPinned?: boolean;
  highlightedIdentifier?: number;
}>();

const emit = defineEmits<{
  'close': [];
  'matched': [];
  'show-in-events': [data: { identifier: number; groupIdentifier: string }];
  'show-unmatched-in-events': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  matchAssetMovement,
  refreshUnmatchedAssetMovements,
} = useUnmatchedAssetMovements();

const { fetchHistoryEvents } = useHistoryEventsApi();
const { getAssetMovementMatches } = useAssetMovementMatchingApi();

const { assetMovementAmountTolerance, assetMovementTimeRange } = storeToRefs(useGeneralSettingsStore());

function getDefaultHourRange(): number {
  return get(assetMovementTimeRange) / 3600;
}

function getDefaultTolerancePercentage(): string {
  return bigNumberify(get(assetMovementAmountTolerance)).multipliedBy(100).toString();
}

const searchLoading = ref<boolean>(false);
const matchingLoading = ref<boolean>(false);
const potentialMatches = ref<PotentialMatchRow[]>([]);
const selectedMatchIds = ref<number[]>([]);
const searchTimeRange = ref<string>(getDefaultHourRange().toString());
const onlyExpectedAssets = ref<boolean>(true);
const tolerancePercentage = ref<string>(getDefaultTolerancePercentage());

function percentageToDecimal(percentage: string): string {
  return bigNumberify(percentage).dividedBy(100).toString();
}
const buttonSize = computed<'sm' | undefined>(() => props.isPinned ? 'sm' : undefined);

function transformToMatchRow(row: HistoryEventCollectionRow, isCloseMatch: boolean): PotentialMatchRow {
  const { entry, ...meta } = getEventEntryFromCollection(row);
  const eventEntry = { ...entry, ...meta };
  return {
    entry: eventEntry,
    identifier: eventEntry.identifier,
    isCloseMatch,
  };
}

async function searchPotentialMatches(): Promise<void> {
  set(searchLoading, true);
  set(potentialMatches, []);

  try {
    const groupIdentifier = props.movement.groupIdentifier;

    const hours = Number.parseInt(get(searchTimeRange), 10) || getDefaultHourRange();
    const timeRangeInSeconds = hours * 60 * 60;

    const suggestions = await getAssetMovementMatches(groupIdentifier, timeRangeInSeconds, get(onlyExpectedAssets), percentageToDecimal(get(tolerancePercentage)));
    const allIdentifiers = [...suggestions.closeMatches, ...suggestions.otherEvents];

    if (allIdentifiers.length === 0) {
      set(potentialMatches, []);
      return;
    }

    const response = await fetchHistoryEvents({
      aggregateByGroupIds: false,
      identifiers: allIdentifiers.map(String),
      limit: -1,
      offset: 0,
    });

    const closeMatchSet = new Set(suggestions.closeMatches);
    const matches = response.entries
      .map(row => transformToMatchRow(row, closeMatchSet.has(getEventEntryFromCollection(row).entry.identifier)));

    const identifierOrderMap = new Map(allIdentifiers.map((id, index) => [id, index]));
    matches.sort((a, b) => {
      const orderA = identifierOrderMap.get(a.entry.identifier) ?? Number.MAX_SAFE_INTEGER;
      const orderB = identifierOrderMap.get(b.entry.identifier) ?? Number.MAX_SAFE_INTEGER;
      return orderA - orderB;
    });

    set(potentialMatches, matches);
  }
  catch (error) {
    logger.error('Failed to search potential matches:', error);
  }
  finally {
    set(searchLoading, false);
  }
}

async function confirmMatch(): Promise<void> {
  const matchIds = get(selectedMatchIds);

  if (matchIds.length === 0)
    return;

  set(matchingLoading, true);

  try {
    const eventEntry = getEventEntryFromCollection(props.movement.events);
    const assetMovementId = eventEntry.entry.identifier;

    if (!assetMovementId)
      return;

    const result = await matchAssetMovement(assetMovementId, matchIds);

    if (result.success) {
      await refreshUnmatchedAssetMovements(true);
      emit('matched');
    }
  }
  finally {
    set(matchingLoading, false);
  }
}

function close(): void {
  emit('close');
}

watchImmediate(() => props.movement, async () => {
  set(potentialMatches, []);
  set(selectedMatchIds, []);
  set(searchTimeRange, getDefaultHourRange().toString());
  set(onlyExpectedAssets, true);
  set(tolerancePercentage, getDefaultTolerancePercentage());
  await searchPotentialMatches();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div
      class="flex-1 overflow-auto"
      :class="isPinned ? 'px-4 py-2' : ''"
    >
      <PotentialMatchesList
        v-model:selected-match-ids="selectedMatchIds"
        v-model:search-time-range="searchTimeRange"
        v-model:only-expected-assets="onlyExpectedAssets"
        v-model:tolerance-percentage="tolerancePercentage"
        :movement="movement"
        :matches="potentialMatches"
        :loading="searchLoading"
        :is-pinned="isPinned"
        :highlighted-identifier="highlightedIdentifier"
        @search="searchPotentialMatches()"
        @show-in-events="emit('show-in-events', $event)"
        @show-unmatched-in-events="emit('show-unmatched-in-events')"
      />
    </div>

    <div
      class="flex justify-end gap-2 shrink-0"
      :class="isPinned ? 'p-2 border-t border-default' : 'py-4'"
    >
      <RuiButton
        variant="text"
        :size="buttonSize"
        @click="close()"
      >
        {{ t('common.actions.cancel') }}
      </RuiButton>
      <RuiButton
        color="primary"
        :size="buttonSize"
        :disabled="selectedMatchIds.length === 0"
        :loading="matchingLoading"
        @click="confirmMatch()"
      >
        {{ t('asset_movement_matching.dialog.confirm_match') }}
        <RuiChip
          v-if="selectedMatchIds.length > 1"
          size="sm"
          class="ml-2 !py-0"
        >
          {{ selectedMatchIds.length }}
        </RuiChip>
      </RuiButton>
    </div>
  </div>
</template>
