<script setup lang="ts">
import type { MatchingFlow } from '@/modules/history/events/matching/types';
import PotentialMatchesContent from '@/modules/history/events/PotentialMatchesContent.vue';
import {
  type UnmatchedBridgeTransaction,
  useBridgeMatchingFlow,
} from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useBridgeUnmatchableExplanation } from '@/modules/history/events/use-untracked-bridge-counterpart';
import { PinnedNames } from '@/modules/session/types';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const modelValue = defineModel<boolean>({ required: true });

const { transaction } = defineProps<{
  transaction: UnmatchedBridgeTransaction;
}>();

const emit = defineEmits<{
  matched: [];
  pinned: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { pin } = usePinnedPanel(PinnedNames.MATCH_BRIDGE_TRANSACTIONS);

const flow: MatchingFlow = useBridgeMatchingFlow();
const { unmatchableExplanation: emptyExplanation } = useBridgeUnmatchableExplanation(() => transaction);

function closeDialog(): void {
  set(modelValue, false);
}

function onMatched(): void {
  set(modelValue, false);
  emit('matched');
}

function showUnmatchedInEvents(): void {
  pin({ highlightedGroupIdentifier: transaction.groupIdentifier });
  set(modelValue, false);
  emit('pinned');
}

function showPotentialMatchInEvents(data: { identifier: number; groupIdentifier: string }): void {
  pin({
    highlightedGroupIdentifier: transaction.groupIdentifier,
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
    <RuiCard content-class="!pb-0">
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
        :movement="transaction"
        :flow="flow"
        :entry-labels="{ locationHeader: t('common.location'), type: transaction.direction }"
        :empty-explanation="emptyExplanation"
        @close="closeDialog()"
        @matched="onMatched()"
        @show-in-events="showPotentialMatchInEvents($event)"
        @show-unmatched-in-events="showUnmatchedInEvents()"
      />
    </RuiCard>
  </RuiDialog>
</template>
