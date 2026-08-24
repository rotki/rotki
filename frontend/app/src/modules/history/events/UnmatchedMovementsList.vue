<script setup lang="ts">
import type { UnmatchedActionPayload } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';
import UnmatchedMovementsCards from '@/modules/history/events/UnmatchedMovementsCards.vue';
import UnmatchedMovementsTable from '@/modules/history/events/UnmatchedMovementsTable.vue';
import { useUnmatchedMovementRows } from '@/modules/history/events/use-unmatched-movement-rows';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';

// The host of the unmatched-movements surface. See UnmatchedBridgesList for the shape: the
// model and both presentations are free of `isPinned`, and only this file reads it.
const selected = defineModel<string[]>('selected', { required: true });

const {
  movements,
  highlightedGroupIdentifier,
  ignoreLoading,
  isPinned,
  showRestore,
  loading,
  matchDisabled,
  matchMinimumTier,
} = defineProps<{
  movements: UnmatchedAssetMovement[];
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  isPinned?: boolean;
  matchDisabled?: boolean;
  matchMinimumTier?: string | null;
  showRestore?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  action: [payload: UnmatchedActionPayload<UnmatchedAssetMovement>];
  pin: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { currentTier, premium } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

const { description, emptyDescription, rows, specFor } = useUnmatchedMovementRows({
  matchDisabled: () => matchDisabled,
  movements: () => movements,
  showRestore: () => showRestore,
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
      :is="isPinned ? UnmatchedMovementsCards : UnmatchedMovementsTable"
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
          variant="asset-movement"
          :premium="premium"
          :current-tier="currentTier"
          :match-minimum-tier="matchMinimumTier"
        />
      </template>
    </Component>
  </div>
</template>
