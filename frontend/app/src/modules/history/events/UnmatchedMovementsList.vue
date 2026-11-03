<script setup lang="ts">
import type { UnmatchedActionPayload, UnmatchedMatchAccess } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import { UnmatchedVariant } from '@/modules/history/events/unmatched-row';
import UnmatchedCards from '@/modules/history/events/UnmatchedCards.vue';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';
import UnmatchedTable from '@/modules/history/events/UnmatchedTable.vue';
import { useUnmatchedMovementRows } from '@/modules/history/events/use-unmatched-movement-rows';

const selected = defineModel<string[]>('selected', { required: true });

const {
  error,
  movements,
  highlightedGroupIdentifier,
  ignoreLoading,
  isPinned,
  showRestore,
  loading,
  matchAccess,
} = defineProps<{
  movements: UnmatchedAssetMovement[];
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  isPinned?: boolean;
  /** absent when matching is not gated at all */
  matchAccess?: UnmatchedMatchAccess;
  showRestore?: boolean;
  loading?: boolean;
  /** why the last load failed, shown in place of the empty text or above the rows it left */
  error?: unknown;
}>();

const emit = defineEmits<{
  action: [payload: UnmatchedActionPayload<UnmatchedAssetMovement>];
  pin: [];
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const matchDisabled = computed<boolean>(() => matchAccess !== undefined && !matchAccess.allowed);

const { description, emptyDescription, failure, rows, specFor } = useUnmatchedMovementRows({
  error: () => error,
  matchDisabled,
  movements: () => movements,
  showRestore: () => showRestore,
});
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
      :is="isPinned ? UnmatchedCards : UnmatchedTable"
      v-model:selected="selected"
      :variant="isPinned ? undefined : UnmatchedVariant.ASSET_MOVEMENT"
      :rows="rows"
      :spec-for="specFor"
      :empty-description="emptyDescription"
      :failure="failure"
      :highlighted-group-identifier="highlightedGroupIdentifier"
      :ignore-loading="ignoreLoading"
      :loading="loading"
      @action="emit('action', $event)"
      @retry="emit('retry')"
    >
      <template
        v-if="matchDisabled"
        #alert
      >
        <UnmatchedMatchDisabledAlert
          :variant="UnmatchedVariant.ASSET_MOVEMENT"
          :count="showRestore ? 0 : movements.length"
          :match-minimum-tier="matchAccess?.minimumTier"
        />
      </template>
    </Component>
  </div>
</template>
