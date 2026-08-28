<script setup lang="ts">
import type { MatchingFlow, UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import { usePotentialMatches } from '@/modules/history/events/matching/use-potential-matches';
import PotentialMatchesList from '@/modules/history/events/PotentialMatchesList.vue';

const { flow, isPinned, movement } = defineProps<{
  movement: UnmatchedEventGroup;
  isPinned?: boolean;
  highlightedIdentifier?: number;
  /**
   * Overrides the default asset-movement matching backend calls, so the same
   * content component can drive other matching flows (e.g. bridge transactions).
   */
  flow?: MatchingFlow;
  /** How the unmatched entry is described in the summary table; see `PotentialMatchesList`. */
  entryLabels?: { type: string; locationHeader: string; matchingFor?: string };
  /** Shown when a search returns no matches, explaining why none can be found. */
  emptyExplanation?: string;
}>();

const emit = defineEmits<{
  'close': [];
  'matched': [];
  'show-in-events': [data: { identifier: number; groupIdentifier: string }];
  'show-unmatched-in-events': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  confirmMatch,
  matchingLoading,
  modelOnlyExpectedAssets: onlyExpectedAssets,
  modelSearchTimeRange: searchTimeRange,
  modelSelectedMatchIds: selectedMatchIds,
  modelTolerancePercentage: tolerancePercentage,
  potentialMatches,
  searchError,
  searchLoading,
  searchPotentialMatches,
} = usePotentialMatches(() => movement, () => flow);

const buttonSize = computed<'sm' | undefined>(() => isPinned ? 'sm' : undefined);

function close(): void {
  emit('close');
}

async function onConfirm(): Promise<void> {
  if (await confirmMatch())
    emit('matched');
}
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
        :entry-labels="entryLabels"
        :search-error="searchError"
        :empty-explanation="emptyExplanation"
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
        @click="onConfirm()"
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
