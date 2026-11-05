<script setup lang="ts" generic="TItem extends UnmatchedEventGroup, TRow extends UnmatchedRow<TItem>">
import type { MatchingKind } from '@/modules/history/events/matching/matching-kind';
import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { UnmatchedActionPayload } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import UnmatchedCards from '@/modules/history/events/UnmatchedCards.vue';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';
import UnmatchedTable from '@/modules/history/events/UnmatchedTable.vue';

const selected = defineModel<string[]>('selected', { required: true });

const {
  error,
  highlightedGroupIdentifier,
  ignoreLoading,
  isPinned,
  items,
  kind,
  loading,
  showRestore,
} = defineProps<{
  kind: MatchingKind<TItem, TRow>;
  items: TItem[];
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  isPinned?: boolean;
  showRestore?: boolean;
  loading?: boolean;
  /** why the last load failed, shown in place of the empty text or above the rows it left */
  error?: unknown;
}>();

const emit = defineEmits<{
  action: [payload: UnmatchedActionPayload<TItem>];
  pin: [];
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { autoMatchMinimumTier, isAutoMatchAllowed } = kind.useSource();

const matchDisabled = computed<boolean>(() => !get(isAutoMatchAllowed));

const { description, emptyDescription, failure, rows, specFor } = kind.useRows({
  error: () => error,
  items: () => items,
  matchDisabled,
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

    <UnmatchedCards
      v-if="isPinned"
      v-model:selected="selected"
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
          :variant="kind.variant"
          :count="showRestore ? 0 : items.length"
          :match-minimum-tier="autoMatchMinimumTier"
        />
      </template>
    </UnmatchedCards>
    <UnmatchedTable
      v-else
      v-model:selected="selected"
      :variant="kind.variant"
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
          :variant="kind.variant"
          :count="showRestore ? 0 : items.length"
          :match-minimum-tier="autoMatchMinimumTier"
        />
      </template>
    </UnmatchedTable>
  </div>
</template>
