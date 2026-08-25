<script setup lang="ts">
import type { MatchingFlow } from '@/modules/history/events/matching/types';
import MatchBridgeTransactionsContent from '@/modules/history/events/MatchBridgeTransactionsContent.vue';
import PotentialMatchesContent from '@/modules/history/events/PotentialMatchesContent.vue';
import { usePinnedMatchPanel } from '@/modules/history/events/use-pinned-match-panel';
import {
  type UnmatchedBridgeTransaction,
  useBridgeEntryLabels,
  useBridgeMatchingFlow,
  useUnmatchedBridgeTransactions,
} from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useBridgeUnmatchableExplanation } from '@/modules/history/events/use-untracked-bridge-counterpart';
import { PinnedNames } from '@/modules/session/types';
import PinnedDetailSheet from '@/modules/shell/pinned/PinnedDetailSheet.vue';

const { highlightedGroupIdentifier, highlightedPotentialMatchIdentifier, potentialMatchGroupIdentifier } = defineProps<{
  highlightedGroupIdentifier?: string;
  highlightedPotentialMatchIdentifier?: number;
  potentialMatchGroupIdentifier?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { ignoredTransactions, unmatchedTransactions } = useUnmatchedBridgeTransactions();

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
  subject: potentialMatchTransaction,
  unpin,
} = usePinnedMatchPanel<UnmatchedBridgeTransaction>({
  getIdentifier: transaction => transaction.identifier,
  highlightedGroupIdentifier: () => highlightedGroupIdentifier,
  highlightedPotentialMatchIdentifier: () => highlightedPotentialMatchIdentifier,
  pinnedName: PinnedNames.MATCH_BRIDGE_TRANSACTIONS,
  potentialMatchGroupIdentifier: () => potentialMatchGroupIdentifier,
  sources: [unmatchedTransactions, ignoredTransactions],
});

const flow: MatchingFlow = useBridgeMatchingFlow();
const { unmatchableExplanation: emptyExplanation } = useBridgeUnmatchableExplanation(potentialMatchTransaction);
const bridgeEntryLabels = useBridgeEntryLabels(potentialMatchTransaction);
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex-1 overflow-hidden flex flex-col relative">
      <MatchBridgeTransactionsContent
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
          v-if="potentialMatchTransaction"
          class="flex-1 h-full"
        >
          <PotentialMatchesContent
            :movement="potentialMatchTransaction"
            :flow="flow"
            :entry-labels="bridgeEntryLabels"
            :highlighted-identifier="activePotentialMatchIdentifier"
            :empty-explanation="emptyExplanation"
            is-pinned
            @close="closeDrawer()"
            @matched="onMatched()"
            @show-in-events="showPotentialMatchInHistoryEvents($event)"
            @show-unmatched-in-events="showInHistoryEvents(potentialMatchTransaction)"
          />
        </div>
      </PinnedDetailSheet>
    </div>
  </div>
</template>
