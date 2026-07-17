<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import MatchAssetMovementsContent from '@/modules/history/events/MatchAssetMovementsContent.vue';
import PotentialMatchesContent from '@/modules/history/events/PotentialMatchesContent.vue';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
import {
  type UnmatchedAssetMovement,
  useUnmatchedAssetMovements,
} from '@/modules/history/events/use-unmatched-asset-movements';
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
const potentialMatchMovement = ref<UnmatchedAssetMovement>();
const showPotentialMatchesDrawer = ref<boolean>(false);

const { isPinned, unpin: unpinPanel } = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);
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
  ignoredMovements,
  unmatchedMovements,
} = useUnmatchedAssetMovements();

function selectMovement(movement: UnmatchedAssetMovement): void {
  const identifier = getEventEntryFromCollection(movement.events).entry.identifier;

  set(potentialMatchMovement, movement);
  set(showPotentialMatchesDrawer, true);
  set(activePotentialMatchIdentifier, undefined);
  set(activeGroupIdentifier, movement.groupIdentifier);

  clearHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH);
  setHighlightTarget(HighlightTargetTypes.ASSET_MOVEMENT, { groupIdentifier: movement.groupIdentifier, identifier });

  requestNavigation({
    highlightedAssetMovement: identifier,
    targetGroupIdentifier: movement.groupIdentifier,
  });
}

async function closePotentialMatchesDrawer(): Promise<void> {
  set(showPotentialMatchesDrawer, false);
  set(potentialMatchMovement, undefined);
  set(activePotentialMatchIdentifier, undefined);
  clearHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH);

  // Clear the green highlight from route while preserving the yellow highlight
  const { highlightedPotentialMatch, ...remainingQuery } = get(route).query;
  if (highlightedPotentialMatch) {
    await router.replace({ query: remainingQuery });
  }
}

// The sheet is only open once a movement is actually selected, so it never flashes empty while the
// close animation drains the movement. Closing routes through the same cleanup as the header button.
const potentialMatchesSheetOpen = computed<boolean>({
  get: () => get(showPotentialMatchesDrawer) && !!get(potentialMatchMovement),
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

function showInHistoryEvents(movement: UnmatchedAssetMovement): void {
  const identifier = getEventEntryFromCollection(movement.events).entry.identifier;

  set(activeGroupIdentifier, movement.groupIdentifier);
  set(activePotentialMatchIdentifier, undefined);
  clearHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH);
  setHighlightTarget(HighlightTargetTypes.ASSET_MOVEMENT, { groupIdentifier: movement.groupIdentifier, identifier });

  requestNavigation({
    highlightedAssetMovement: identifier,
    targetGroupIdentifier: movement.groupIdentifier,
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
 * Navigate to the highlighted movement if it exists.
 * Returns true if navigation was triggered, false otherwise.
 */
function navigateToHighlightedMovement(targetGroupIdentifier: string): boolean {
  const unmatched = get(unmatchedMovements);
  const ignored = get(ignoredMovements);

  const movement = unmatched.find(m => m.groupIdentifier === targetGroupIdentifier)
    || ignored.find(m => m.groupIdentifier === targetGroupIdentifier);

  if (movement) {
    // If potential match identifier is also provided, open the drawer and navigate to potential match
    if (highlightedPotentialMatchIdentifier && potentialMatchGroupIdentifier) {
      const identifier = getEventEntryFromCollection(movement.events).entry.identifier;
      set(potentialMatchMovement, movement);
      set(showPotentialMatchesDrawer, true);
      set(activeGroupIdentifier, movement.groupIdentifier);
      showPotentialMatchInHistoryEvents(
        {
          groupIdentifier: potentialMatchGroupIdentifier,
          identifier: highlightedPotentialMatchIdentifier,
        },
        identifier,
      );
    }
    else {
      showInHistoryEvents(movement);
    }
    return true;
  }
  return false;
}

// Watch for data to load and navigate to initial highlight if provided
watch([unmatchedMovements, ignoredMovements], () => {
  const initialHighlight = highlightedGroupIdentifier;
  if (!initialHighlight || get(hasNavigatedToInitialHighlight))
    return;

  if (navigateToHighlightedMovement(initialHighlight)) {
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
  navigateToHighlightedMovement(newHighlight);
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
        @select="selectMovement($event)"
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
          v-if="potentialMatchMovement"
          class="flex-1 h-full"
        >
          <PotentialMatchesContent
            :movement="potentialMatchMovement"
            :highlighted-identifier="activePotentialMatchIdentifier"
            is-pinned
            @close="closePotentialMatchesDrawer()"
            @matched="onPinnedMatched()"
            @show-in-events="showPotentialMatchInHistoryEvents($event)"
            @show-unmatched-in-events="showInHistoryEvents(potentialMatchMovement)"
          />
        </div>
      </PinnedDetailSheet>
    </div>
  </div>
</template>
