<script setup lang="ts">
import type { Nullable } from '@rotki/common';
import type { Pinned } from '@/types/session';
import { startPromise } from '@shared/utils';
import MatchAssetMovementsContent from '@/components/history/events/MatchAssetMovementsContent.vue';
import PotentialMatchesContent from '@/components/history/events/PotentialMatchesContent.vue';
import { useHistoryEventNavigation } from '@/composables/history/events/use-history-event-navigation';
import {
  type UnmatchedAssetMovement,
  useUnmatchedAssetMovements,
} from '@/composables/history/events/use-unmatched-asset-movements';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { getEventEntryFromCollection } from '@/utils/history/events';

const props = defineProps<{
  highlightedGroupIdentifier?: string;
  highlightedPotentialMatchIdentifier?: number;
  potentialMatchGroupIdentifier?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const activeGroupIdentifier = ref<string | undefined>(props.highlightedGroupIdentifier);
const activePotentialMatchIdentifier = ref<number | undefined>(props.highlightedPotentialMatchIdentifier);
const potentialMatchMovement = ref<UnmatchedAssetMovement>();
const showPotentialMatchesDrawer = ref<boolean>(false);

const { pinned, showPinned } = storeToRefs(useAreaVisibilityStore());
const { clearAllHighlightTargets, clearHighlightTarget, requestNavigation, setHighlightTarget } = useHistoryEventNavigation();

const {
  ignoredMovements,
  unmatchedMovements,
} = useUnmatchedAssetMovements();

async function clearHighlight(): Promise<void> {
  set(activeGroupIdentifier, undefined);
  set(activePotentialMatchIdentifier, undefined);
  clearAllHighlightTargets();
  const { highlightedAssetMovement, highlightedPotentialMatch, ...remainingQuery } = get(route).query;
  if (highlightedAssetMovement || highlightedPotentialMatch) {
    await router.replace({ query: remainingQuery });
  }
}

function selectMovement(movement: UnmatchedAssetMovement): void {
  const identifier = getEventEntryFromCollection(movement.events).entry.identifier;

  set(potentialMatchMovement, movement);
  set(showPotentialMatchesDrawer, true);
  set(activePotentialMatchIdentifier, undefined);
  set(activeGroupIdentifier, movement.groupIdentifier);

  clearHighlightTarget('potentialMatch');
  setHighlightTarget('assetMovement', { groupIdentifier: movement.groupIdentifier, identifier });

  requestNavigation({
    highlightedAssetMovement: identifier,
    targetGroupIdentifier: movement.groupIdentifier,
  });
}

async function closePotentialMatchesDrawer(): Promise<void> {
  set(showPotentialMatchesDrawer, false);
  set(potentialMatchMovement, undefined);
  set(activePotentialMatchIdentifier, undefined);
  clearHighlightTarget('potentialMatch');

  // Clear the green highlight from route while preserving the yellow highlight
  const { highlightedPotentialMatch, ...remainingQuery } = get(route).query;
  if (highlightedPotentialMatch) {
    await router.replace({ query: remainingQuery });
  }
}

async function onPinnedMatched(): Promise<void> {
  await closePotentialMatchesDrawer();
  await clearHighlight();
}

function setPinned(pin: Nullable<Pinned>): void {
  set(pinned, pin);
}

async function unpin(): Promise<void> {
  await clearHighlight();
  setPinned(null);
}

function closePinnedSidebar(): void {
  set(showPinned, false);
}

function showInHistoryEvents(movement: UnmatchedAssetMovement): void {
  const identifier = getEventEntryFromCollection(movement.events).entry.identifier;

  set(activeGroupIdentifier, movement.groupIdentifier);
  set(activePotentialMatchIdentifier, undefined);
  clearHighlightTarget('potentialMatch');
  setHighlightTarget('assetMovement', { groupIdentifier: movement.groupIdentifier, identifier });

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
  setHighlightTarget('potentialMatch', { groupIdentifier: data.groupIdentifier, identifier: data.identifier });

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
    if (props.highlightedPotentialMatchIdentifier && props.potentialMatchGroupIdentifier) {
      const identifier = getEventEntryFromCollection(movement.events).entry.identifier;
      set(potentialMatchMovement, movement);
      set(showPotentialMatchesDrawer, true);
      set(activeGroupIdentifier, movement.groupIdentifier);
      showPotentialMatchInHistoryEvents(
        {
          groupIdentifier: props.potentialMatchGroupIdentifier,
          identifier: props.highlightedPotentialMatchIdentifier,
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
  const initialHighlight = props.highlightedGroupIdentifier;
  if (!initialHighlight || get(hasNavigatedToInitialHighlight))
    return;

  if (navigateToHighlightedMovement(initialHighlight)) {
    set(hasNavigatedToInitialHighlight, true);
  }
});

// Watch for prop changes to handle navigation when pinned section is already open
watch(() => props.highlightedGroupIdentifier, (newHighlight, oldHighlight) => {
  // Only trigger if the highlight actually changed (not on initial mount)
  if (!newHighlight || newHighlight === oldHighlight)
    return;

  // Update local ref and navigate to the new highlight
  set(activeGroupIdentifier, newHighlight);
  navigateToHighlightedMovement(newHighlight);
});

onUnmounted(() => {
  startPromise(clearHighlight());
});
</script>

<template>
  <RuiCard
    no-padding
    class="overflow-hidden !rounded-none h-full flex flex-col"
    variant="flat"
  >
    <div class="flex items-center bg-rui-primary text-white p-2 shrink-0">
      <RuiButton
        variant="text"
        size="sm"
        icon
        @click="closePinnedSidebar()"
      >
        <RuiIcon
          class="text-white"
          name="lu-chevron-right"
          size="20"
        />
      </RuiButton>

      <h6 class="flex items-center text-body-1 pl-2">
        {{ t('asset_movement_matching.dialog.title') }}
      </h6>

      <div class="grow" />

      <RuiTooltip
        :popper="{ placement: 'bottom' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            size="sm"
            @click="unpin()"
          >
            <RuiIcon
              size="20"
              class="text-white"
              name="lu-x"
            />
          </RuiButton>
        </template>
        {{ t('asset_movement_matching.actions_pin.unpin_section') }}
      </RuiTooltip>
    </div>

    <div class="flex-1 overflow-hidden flex flex-col relative">
      <MatchAssetMovementsContent
        :highlighted-group-identifier="activeGroupIdentifier"
        :on-action-complete="clearHighlight"
        is-pinned
        @pin="unpin()"
        @select="selectMovement($event)"
        @show-in-events="showInHistoryEvents($event)"
      />

      <!-- Overlay backdrop -->
      <Transition
        enter-active-class="transition-opacity duration-300"
        leave-active-class="transition-opacity duration-300"
        enter-from-class="opacity-0"
        leave-to-class="opacity-0"
      >
        <div
          v-if="showPotentialMatchesDrawer && potentialMatchMovement"
          class="absolute inset-0 bg-black/50"
          @click="closePotentialMatchesDrawer()"
        />
      </Transition>

      <!-- Bottom drawer for potential matches (slides up from bottom) -->
      <Transition
        enter-active-class="transition-transform duration-300 ease-out"
        leave-active-class="transition-transform duration-300 ease-out"
        enter-from-class="translate-y-full"
        leave-to-class="translate-y-full"
      >
        <RuiCard
          v-if="showPotentialMatchesDrawer && potentialMatchMovement"
          no-padding
          class="absolute bottom-0 left-0 right-0 h-[95%] border-t-2 border-rui-primary flex flex-col shadow-lg !rounded-b-none z-10 overflow-hidden"
          content-class="h-full"
        >
          <template #custom-header>
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
          <div class="flex-1 h-full">
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
        </RuiCard>
      </Transition>
    </div>
  </RuiCard>
</template>
