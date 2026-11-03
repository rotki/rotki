<script setup lang="ts" generic="TItem extends UnmatchedEventGroup, TRow extends UnmatchedRow<TItem>">
import type { MatchingKind } from '@/modules/history/events/matching/matching-kind';
import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import UnmatchedMatchingContent from '@/modules/history/events/UnmatchedMatchingContent.vue';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const modelValue = defineModel<boolean>({ default: false });

const { kind } = defineProps<{
  kind: MatchingKind<TItem, TRow>;
}>();

const emit = defineEmits<{
  'find-match': [item: TItem];
}>();

const { t } = useI18n({ useScope: 'global' });

const { pin } = usePinnedPanel(kind.pinnedName);

function closeDialog(): void {
  set(modelValue, false);
}

function pinSection(highlightedGroupIdentifier?: string): void {
  pin(highlightedGroupIdentifier ? { highlightedGroupIdentifier } : {});
  set(modelValue, false);
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="1000"
  >
    <RuiCard
      :class-names="{ content: 'py-0!' }"
      divide
    >
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 py-2">
          <CardTitle>
            {{ t(kind.messages.title) }}
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

      <UnmatchedMatchingContent
        :kind="kind"
        @close="closeDialog()"
        @pin="pinSection()"
        @select="emit('find-match', $event)"
        @show-in-events="pinSection($event.groupIdentifier)"
      />
    </RuiCard>
  </RuiDialog>
</template>
