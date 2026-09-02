<script setup lang="ts">
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import MatchBridgeTransactionsContent from '@/modules/history/events/MatchBridgeTransactionsContent.vue';
import { PinnedNames } from '@/modules/session/types';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const modelValue = defineModel<boolean>({ default: false });

const emit = defineEmits<{
  'find-match': [transaction: UnmatchedBridgeTransaction];
}>();

const { t } = useI18n({ useScope: 'global' });

const { pin } = usePinnedPanel(PinnedNames.MATCH_BRIDGE_TRANSACTIONS);

function selectTransaction(transaction: UnmatchedBridgeTransaction): void {
  emit('find-match', transaction);
}

function closeDialog(): void {
  set(modelValue, false);
}

function pinSection(highlightedGroupIdentifier?: string): void {
  pin(highlightedGroupIdentifier ? { highlightedGroupIdentifier } : {});
  set(modelValue, false);
}

function showInHistoryEvents(transaction: UnmatchedBridgeTransaction): void {
  pinSection(transaction.groupIdentifier);
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="1000"
  >
    <RuiCard
      :class-names="{ content: '!py-0' }"
      divide
    >
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 py-2">
          <CardTitle>
            {{ t('bridge_matching.dialog.title') }}
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

      <MatchBridgeTransactionsContent
        @close="closeDialog()"
        @pin="pinSection()"
        @select="selectTransaction($event)"
        @show-in-events="showInHistoryEvents($event)"
      />
    </RuiCard>
  </RuiDialog>
</template>
