<script setup lang="ts" generic="TItem extends UnmatchedEventGroup, TRow extends UnmatchedRow<TItem>">
import type { MatchingKind } from '@/modules/history/events/matching/matching-kind';
import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import PotentialMatchesContent from '@/modules/history/events/PotentialMatchesContent.vue';
import UnmatchedMatchingContent from '@/modules/history/events/UnmatchedMatchingContent.vue';
import { usePinnedMatchPanel } from '@/modules/history/events/use-pinned-match-panel';
import PinnedDetailSheet from '@/modules/shell/pinned/PinnedDetailSheet.vue';

const { highlightedGroupIdentifier, highlightedPotentialMatchIdentifier, kind, potentialMatchGroupIdentifier } = defineProps<{
  kind: MatchingKind<TItem, TRow>;
  highlightedGroupIdentifier?: string;
  highlightedPotentialMatchIdentifier?: number;
  potentialMatchGroupIdentifier?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { ignored, unmatched } = kind.useSource();

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
  subject,
  unpin,
} = usePinnedMatchPanel<TItem>({
  getIdentifier: kind.getIdentifier,
  highlightedGroupIdentifier: () => highlightedGroupIdentifier,
  highlightedPotentialMatchIdentifier: () => highlightedPotentialMatchIdentifier,
  pinnedName: kind.pinnedName,
  potentialMatchGroupIdentifier: () => potentialMatchGroupIdentifier,
  sources: [unmatched, ignored],
});

const flow = kind.useFlow();
const entryLabels = kind.useEntryLabels(() => get(subject));
const emptyExplanation = kind.useUnmatchableExplanation(() => get(subject));
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex-1 overflow-hidden flex flex-col relative">
      <UnmatchedMatchingContent
        :kind="kind"
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
          v-if="subject"
          class="flex-1 h-full"
        >
          <PotentialMatchesContent
            :movement="subject"
            :flow="flow"
            :entry-labels="entryLabels"
            :highlighted-identifier="activePotentialMatchIdentifier"
            :empty-explanation="emptyExplanation"
            is-pinned
            @close="closeDrawer()"
            @matched="onMatched()"
            @show-in-events="showPotentialMatchInHistoryEvents($event)"
            @show-unmatched-in-events="showInHistoryEvents(subject)"
          />
        </div>
      </PinnedDetailSheet>
    </div>
  </div>
</template>
