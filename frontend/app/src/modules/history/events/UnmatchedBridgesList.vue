<script setup lang="ts">
import type { UnmatchedActionPayload } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import UnmatchedBridgesCards from '@/modules/history/events/UnmatchedBridgesCards.vue';
import UnmatchedBridgesTable from '@/modules/history/events/UnmatchedBridgesTable.vue';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';
import { useUnmatchedBridgeRows } from '@/modules/history/events/use-unmatched-bridge-rows';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';

// The host of the unmatched-bridges surface: it builds the model once and then picks a
// presentation. This is the only file that knows the panel can be pinned - both the model
// and the two presentations are written without that flag, so a change to what a row offers
// lands in one place and reaches both.
const selected = defineModel<string[]>('selected', { required: true });

const {
  transactions,
  highlightedGroupIdentifier,
  ignoreLoading,
  isPinned,
  showRestore,
  loading,
  matchDisabled,
  matchMinimumTier,
} = defineProps<{
  transactions: UnmatchedBridgeTransaction[];
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  isPinned?: boolean;
  matchDisabled?: boolean;
  matchMinimumTier?: string | null;
  showRestore?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  action: [payload: UnmatchedActionPayload<UnmatchedBridgeTransaction>];
  pin: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { currentTier, premium } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

const { description, emptyDescription, rows, specFor } = useUnmatchedBridgeRows({
  matchDisabled: () => matchDisabled,
  showRestore: () => showRestore,
  transactions: () => transactions,
});

// Pinned, the host is a bounded flex column, so the card list is sized by what is left over
// and the pager stays in view. The dialog cannot propagate a height down to the table, so it
// keeps its viewport cap.
const maxHeight = 'calc(100vh - 23rem)';
</script>

<template>
  <div :class="isPinned ? 'flex-1 min-h-0 flex flex-col' : ''">
    <div class="shrink-0 flex items-center justify-between gap-2 mb-4">
      <p class="text-body-2 text-rui-text-secondary">
        {{ description }}
      </p>
      <RuiButton
        v-if="!isPinned"
        size="sm"
        color="primary"
        variant="outlined"
        @click="emit('pin')"
      >
        <template #prepend>
          <RuiIcon
            size="18"
            name="lu-pin"
          />
        </template>
        {{ t('asset_movement_matching.actions_pin.pin_section') }}
      </RuiButton>
    </div>

    <Component
      :is="isPinned ? UnmatchedBridgesCards : UnmatchedBridgesTable"
      v-model:selected="selected"
      :rows="rows"
      :spec-for="specFor"
      :empty-description="emptyDescription"
      :max-height="isPinned ? undefined : maxHeight"
      :highlighted-group-identifier="highlightedGroupIdentifier"
      :ignore-loading="ignoreLoading"
      :loading="loading"
      @action="emit('action', $event)"
    >
      <template
        v-if="matchDisabled"
        #alert
      >
        <UnmatchedMatchDisabledAlert
          variant="bridge"
          :premium="premium"
          :current-tier="currentTier"
          :match-minimum-tier="matchMinimumTier"
        />
      </template>
    </Component>
  </div>
</template>
