<script setup lang="ts" generic="TItem extends UnmatchedEventGroup, TRow extends UnmatchedRow<TItem>">
import type { MatchingKind } from '@/modules/history/events/matching/matching-kind';
import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import PotentialMatchesContent from '@/modules/history/events/PotentialMatchesContent.vue';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const modelValue = defineModel<boolean>({ required: true });

const { item, kind } = defineProps<{
  kind: MatchingKind<TItem, TRow>;
  item: TItem;
}>();

const emit = defineEmits<{
  matched: [];
  pinned: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { pin } = usePinnedPanel(kind.pinnedName);

const flow = kind.useFlow();
const entryLabels = kind.useEntryLabels(() => item);
const emptyExplanation = kind.useUnmatchableExplanation(() => item);

function closeDialog(): void {
  set(modelValue, false);
}

function onMatched(): void {
  set(modelValue, false);
  emit('matched');
}

function showUnmatchedInEvents(): void {
  pin({ highlightedGroupIdentifier: item.groupIdentifier });
  set(modelValue, false);
  emit('pinned');
}

function showPotentialMatchInEvents(data: { identifier: number; groupIdentifier: string }): void {
  pin({
    highlightedGroupIdentifier: item.groupIdentifier,
    highlightedPotentialMatchIdentifier: data.identifier,
    potentialMatchGroupIdentifier: data.groupIdentifier,
  });
  set(modelValue, false);
  emit('pinned');
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="1000"
  >
    <RuiCard
      class="max-h-[90vh] flex flex-col overflow-hidden"
      :class-names="{ content: 'pb-0! flex flex-col flex-1 min-h-0 overflow-hidden' }"
    >
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

      <PotentialMatchesContent
        :movement="item"
        :flow="flow"
        :entry-labels="entryLabels"
        :empty-explanation="emptyExplanation"
        @close="closeDialog()"
        @matched="onMatched()"
        @show-in-events="showPotentialMatchInEvents($event)"
        @show-unmatched-in-events="showUnmatchedInEvents()"
      />
    </RuiCard>
  </RuiDialog>
</template>
