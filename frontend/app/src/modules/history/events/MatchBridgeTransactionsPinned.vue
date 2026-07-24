<script setup lang="ts">
import type { MatchingFlow } from '@/modules/history/events/matching/types';
import { startPromise } from '@shared/utils';
import MatchBridgeTransactionsContent from '@/modules/history/events/MatchBridgeTransactionsContent.vue';
import PotentialMatchesContent from '@/modules/history/events/PotentialMatchesContent.vue';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
import {
  type UnmatchedBridgeTransaction,
  useBridgeMatchingFlow,
  useUnmatchedBridgeTransactions,
} from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useBridgeUnmatchableExplanation } from '@/modules/history/events/use-untracked-bridge-counterpart';
import { PinnedNames } from '@/modules/session/types';
import PinnedDetailSheet from '@/modules/shell/pinned/PinnedDetailSheet.vue';
import { usePinnedHighlightNavigation } from '@/modules/shell/pinned/use-pinned-highlight-navigation';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const { highlightedGroupIdentifier, highlightedPotentialMatchIdentifier, potentialMatchGroupIdentifier } = defineProps<{
  highlightedGroupIdentifier?: string;
  highlightedPotentialMatchIdentifier?: number;
  potentialMatchGroupIdentifier?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const activeGroupIdentifier = ref<string | undefined>(highlightedGroupIdentifier);
const activePotentialMatchIdentifier = ref<number | undefined>(highlightedPotentialMatchIdentifier);
const potentialMatchTransaction = ref<UnmatchedBridgeTransaction>();
const showPotentialMatchesDrawer = ref<boolean>(false);

const { isPinned, unpin: unpinPanel } = usePinnedPanel(PinnedNames.MATCH_BRIDGE_TRANSACTIONS);
const {
  clearHighlightTarget,
  requestNavigation,
  setHighlightTarget,
} = useHistoryEventNavigation();

const { clearHighlight } = usePinnedHighlightNavigation(
  ['highlightedAssetMovement', 'highlightedPotentialMatch'],
  () => {
    set(activeGroupIdentifier, undefined);
    set(activePotentialMatchIdentifier, undefined);
  },
  () => get(isPinned),
);

const {
  ignoredTransactions,
  unmatchedTransactions,
} = useUnmatchedBridgeTransactions();

const flow: MatchingFlow = useBridgeMatchingFlow();
const { unmatchableExplanation: emptyExplanation } = useBridgeUnmatchableExplanation(potentialMatchTransaction);

function selectTransaction(transaction: UnmatchedBridgeTransaction): void {
  const identifier = transaction.identifier;

  set(potentialMatchTransaction, transaction);
  set(showPotentialMatchesDrawer, true);
  set(activePotentialMatchIdentifier, undefined);
  set(activeGroupIdentifier, transaction.groupIdentifier);

  clearHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH);
  setHighlightTarget(HighlightTargetTypes.ASSET_MOVEMENT, { groupIdentifier: transaction.groupIdentifier, identifier });

  requestNavigation({
    highlightedAssetMovement: identifier,
    targetGroupIdentifier: transaction.groupIdentifier,
  });
}

async function closePotentialMatchesDrawer(): Promise<void> {
  set(showPotentialMatchesDrawer, false);
  set(potentialMatchTransaction, undefined);
  set(activePotentialMatchIdentifier, undefined);
  clearHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH);

  // Clear the green highlight from route while preserving the yellow highlight
  const { highlightedPotentialMatch, ...remainingQuery } = get(route).query;
  if (highlightedPotentialMatch) {
    await router.replace({ query: remainingQuery });
  }
}

// The sheet is only open once a transaction is actually selected, so it never flashes empty while
// the close animation drains it. Closing routes through the same cleanup as the header button.
const potentialMatchesSheetOpen = computed<boolean>({
  get: () => get(showPotentialMatchesDrawer) && !!get(potentialMatchTransaction),
  set: (value) => {
    if (!value)
      startPromise(closePotentialMatchesDrawer());
  },
});

async function onPinnedMatched(): Promise<void> {
  await closePotentialMatchesDrawer();
  await clearHighlight();
}

async function unpin(): Promise<void> {
  await clearHighlight();
  unpinPanel();
}

function showInHistoryEvents(transaction: UnmatchedBridgeTransaction): void {
  const identifier = transaction.identifier;

  set(activeGroupIdentifier, transaction.groupIdentifier);
  set(activePotentialMatchIdentifier, undefined);
  clearHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH);
  setHighlightTarget(HighlightTargetTypes.ASSET_MOVEMENT, { groupIdentifier: transaction.groupIdentifier, identifier });

  requestNavigation({
    highlightedAssetMovement: identifier,
    targetGroupIdentifier: transaction.groupIdentifier,
  });
}

function showPotentialMatchInHistoryEvents(
  data: { identifier: number; groupIdentifier: string },
  unmatchedIdentifier?: number,
): void {
  set(activePotentialMatchIdentifier, data.identifier);
  setHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH, { groupIdentifier: data.groupIdentifier, identifier: data.identifier });

  const yellowHighlight = unmatchedIdentifier
    ?? (Number(get(route).query.highlightedAssetMovement) || undefined);

  requestNavigation({
    highlightedAssetMovement: yellowHighlight,
    highlightedPotentialMatch: data.identifier,
    targetGroupIdentifier: data.groupIdentifier,
  });
}

const hasNavigatedToInitialHighlight = ref<boolean>(false);

/**
 * Navigate to the highlighted transaction if it exists.
 * Returns true if navigation was triggered, false otherwise.
 */
function navigateToHighlightedTransaction(targetGroupIdentifier: string): boolean {
  const unmatched = get(unmatchedTransactions);
  const ignored = get(ignoredTransactions);

  const transaction = unmatched.find(tx => tx.groupIdentifier === targetGroupIdentifier)
    || ignored.find(tx => tx.groupIdentifier === targetGroupIdentifier);

  if (transaction) {
    // If potential match identifier is also provided, open the drawer and navigate to potential match
    if (highlightedPotentialMatchIdentifier && potentialMatchGroupIdentifier) {
      const identifier = transaction.identifier;
      set(potentialMatchTransaction, transaction);
      set(showPotentialMatchesDrawer, true);
      set(activeGroupIdentifier, transaction.groupIdentifier);
      showPotentialMatchInHistoryEvents(
        {
          groupIdentifier: potentialMatchGroupIdentifier,
          identifier: highlightedPotentialMatchIdentifier,
        },
        identifier,
      );
    }
    else {
      showInHistoryEvents(transaction);
    }
    return true;
  }
  return false;
}

// Watch for data to load and navigate to initial highlight if provided
watch([unmatchedTransactions, ignoredTransactions], () => {
  const initialHighlight = highlightedGroupIdentifier;
  if (!initialHighlight || get(hasNavigatedToInitialHighlight))
    return;

  if (navigateToHighlightedTransaction(initialHighlight)) {
    set(hasNavigatedToInitialHighlight, true);
  }
});

// Watch for prop changes to handle navigation when pinned section is already open
watch(() => highlightedGroupIdentifier, (newHighlight, oldHighlight) => {
  // Only trigger if the highlight actually changed (not on initial mount)
  if (!newHighlight || newHighlight === oldHighlight)
    return;

  // Update local ref and navigate to the new highlight
  set(activeGroupIdentifier, newHighlight);
  navigateToHighlightedTransaction(newHighlight);
});
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex-1 overflow-hidden flex flex-col relative">
      <MatchBridgeTransactionsContent
        :highlighted-group-identifier="activeGroupIdentifier"
        :on-action-complete="clearHighlight"
        is-pinned
        @pin="unpin()"
        @select="selectTransaction($event)"
        @show-in-events="showInHistoryEvents($event)"
      />

      <PinnedDetailSheet v-model="potentialMatchesSheetOpen">
        <template #header>
          <div class="flex items-center justify-between bg-rui-grey-200 dark:bg-rui-grey-800 px-4 py-2 shrink-0">
            <span class="text-body-2 font-medium">
              {{ t('asset_movement_matching.dialog.select_match_title') }}
            </span>
            <RuiButton
              variant="text"
              icon
              size="sm"
              @click="closePotentialMatchesDrawer()"
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
            :type-label="potentialMatchTransaction.direction"
            :location-header="t('common.location')"
            :highlighted-identifier="activePotentialMatchIdentifier"
            :empty-explanation="emptyExplanation"
            is-pinned
            @close="closePotentialMatchesDrawer()"
            @matched="onPinnedMatched()"
            @show-in-events="showPotentialMatchInHistoryEvents($event)"
            @show-unmatched-in-events="showInHistoryEvents(potentialMatchTransaction)"
          />
        </div>
      </PinnedDetailSheet>
    </div>
  </div>
</template>
