<script setup lang="ts">
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import MatchAssetMovementsContent from '@/modules/history/events/MatchAssetMovementsContent.vue';
import PotentialMatchesContent from '@/modules/history/events/PotentialMatchesContent.vue';
import { usePinnedMatchPanel } from '@/modules/history/events/use-pinned-match-panel';
import {
  type UnmatchedAssetMovement,
  useUnmatchedAssetMovements,
} from '@/modules/history/events/use-unmatched-asset-movements';
import { PinnedNames } from '@/modules/session/types';
import PinnedDetailSheet from '@/modules/shell/pinned/PinnedDetailSheet.vue';

const { highlightedGroupIdentifier, highlightedPotentialMatchIdentifier, potentialMatchGroupIdentifier } = defineProps<{
  highlightedGroupIdentifier?: string;
  highlightedPotentialMatchIdentifier?: number;
  potentialMatchGroupIdentifier?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { ignoredMovements, unmatchedMovements } = useUnmatchedAssetMovements();

const {
  activeGroupIdentifier,
  activePotentialMatchIdentifier,
  clearHighlight,
  closeDrawer,
  modelSheetOpen,
  onMatched,
  select,
  showInHistoryEvents,
  showPotentialMatchInHistoryEvents,
  subject: potentialMatchMovement,
  unpin,
} = usePinnedMatchPanel<UnmatchedAssetMovement>({
  getIdentifier: movement => getEventEntryFromCollection(movement.events).entry.identifier,
  highlightedGroupIdentifier: () => highlightedGroupIdentifier,
  highlightedPotentialMatchIdentifier: () => highlightedPotentialMatchIdentifier,
  pinnedName: PinnedNames.MATCH_ASSET_MOVEMENTS,
  potentialMatchGroupIdentifier: () => potentialMatchGroupIdentifier,
  sources: [unmatchedMovements, ignoredMovements],
});
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex-1 overflow-hidden flex flex-col relative">
      <MatchAssetMovementsContent
        :highlighted-group-identifier="activeGroupIdentifier"
        :on-action-complete="clearHighlight"
        is-pinned
        @pin="unpin()"
        @select="select($event)"
        @show-in-events="showInHistoryEvents($event)"
      />

      <PinnedDetailSheet
        v-model="modelSheetOpen"
        :label="t('asset_movement_matching.dialog.select_match_title')"
      >
        <template #header>
          <div class="flex items-center justify-between bg-rui-grey-200 dark:bg-rui-grey-800 px-4 py-2 shrink-0">
            <span class="text-body-2 font-medium">
              {{ t('asset_movement_matching.dialog.select_match_title') }}
            </span>
            <RuiButton
              variant="text"
              icon
              size="sm"
              @click="closeDrawer()"
            >
              <RuiIcon
                name="lu-x"
                size="16"
              />
            </RuiButton>
          </div>
        </template>
        <div
          v-if="potentialMatchMovement"
          class="flex-1 h-full"
        >
          <PotentialMatchesContent
            :movement="potentialMatchMovement"
            :highlighted-identifier="activePotentialMatchIdentifier"
            is-pinned
            @close="closeDrawer()"
            @matched="onMatched()"
            @show-in-events="showPotentialMatchInHistoryEvents($event)"
            @show-unmatched-in-events="showInHistoryEvents(potentialMatchMovement)"
          />
        </div>
      </PinnedDetailSheet>
    </div>
  </div>
</template>
