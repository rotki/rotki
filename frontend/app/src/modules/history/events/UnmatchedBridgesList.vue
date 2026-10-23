<script setup lang="ts">
import type { UnmatchedActionPayload, UnmatchedMatchAccess } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { HISTORY_DIALOG_MAX_HEIGHT } from '@/modules/history/events/dialog-layout';
import UnmatchedBridgesCards from '@/modules/history/events/UnmatchedBridgesCards.vue';
import UnmatchedBridgesTable from '@/modules/history/events/UnmatchedBridgesTable.vue';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';
import { useUnmatchedBridgeRows } from '@/modules/history/events/use-unmatched-bridge-rows';

const selected = defineModel<string[]>('selected', { required: true });

const {
  error,
  transactions,
  highlightedGroupIdentifier,
  ignoreLoading,
  isPinned,
  showRestore,
  loading,
  matchAccess,
} = defineProps<{
  transactions: UnmatchedBridgeTransaction[];
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
  action: [payload: UnmatchedActionPayload<UnmatchedBridgeTransaction>];
  pin: [];
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const matchDisabled = computed<boolean>(() => matchAccess !== undefined && !matchAccess.allowed);

const { description, emptyDescription, failure, rows, specFor } = useUnmatchedBridgeRows({
  error: () => error,
  matchDisabled,
  showRestore: () => showRestore,
  transactions: () => transactions,
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
      :is="isPinned ? UnmatchedBridgesCards : UnmatchedBridgesTable"
      v-model:selected="selected"
      :rows="rows"
      :spec-for="specFor"
      :empty-description="emptyDescription"
      :failure="failure"
      :max-height="isPinned ? undefined : HISTORY_DIALOG_MAX_HEIGHT"
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
          variant="bridge"
          :count="showRestore ? 0 : transactions.length"
          :match-minimum-tier="matchAccess?.minimumTier"
        />
      </template>
    </Component>
  </div>
</template>
