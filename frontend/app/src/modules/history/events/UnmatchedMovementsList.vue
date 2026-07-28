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

const descriptionEl = useTemplateRef<HTMLElement>('description');
const { height: descriptionHeight } = useElementSize(descriptionEl);

const maxHeight = computed<string>(() =>
  isPinned
    // the card list keeps its select-all bar and pager outside the scroll area,
    // so it gets less room than the table did at the same width
    ? `calc(100vh - 20rem - ${get(descriptionHeight)}px)`
    : 'calc(100vh - 23rem)',
);
</script>

<template>
  <div>
    <div class="flex items-center justify-between gap-2 mb-4">
      <p
        ref="description"
        class="text-body-2 text-rui-text-secondary"
      >
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
      :max-height="maxHeight"
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
