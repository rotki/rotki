<script setup lang="ts" generic="TItem extends UnmatchedEventGroup, TRow extends UnmatchedRow<TItem>">
import type { MatchingKind } from '@/modules/history/events/matching/matching-kind';
import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { UnmatchedActionPayload } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import UnmatchedCards from '@/modules/history/events/UnmatchedCards.vue';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';
import UnmatchedTable from '@/modules/history/events/UnmatchedTable.vue';
import { useSmallValueRows } from '@/modules/history/events/use-small-value-rows';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

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

const { enabled: smallValueEnabled, hiddenIds, threshold, visibleRows } = useSmallValueRows(rows);

const hiddenCount = computed<number>(() => get(hiddenIds).size);

const thresholdValue = computed<BigNumber>(() => bigNumberify(get(threshold)));

/** Drops the rows that just got hidden from the selection, so a bulk action never reaches a row out of view. */
function deselectHidden(hidden: Set<string>): void {
  const current = get(selected);
  if (current.some(id => hidden.has(id)))
    set(selected, current.filter(id => !hidden.has(id)));
}

watch(hiddenIds, deselectHidden);
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

    <div
      v-if="smallValueEnabled"
      class="shrink-0 flex flex-wrap items-center gap-x-4 mb-2"
      data-testid="unmatched-small-value"
    >
      <SettingSwitch
        setting="hideSmallValueMovements"
        size="sm"
        details="auto"
        data-testid="unmatched-small-value-toggle"
        :label="t('asset_movement_matching.small_value.hide')"
        :error-message="t('asset_movement_matching.small_value.error')"
      />
      <i18n-t
        v-if="hiddenCount > 0"
        keypath="asset_movement_matching.small_value.hidden"
        :plural="hiddenCount"
        tag="span"
        scope="global"
        class="text-body-2 text-rui-text-secondary"
        data-testid="unmatched-small-value-hidden"
      >
        <template #count>
          {{ hiddenCount }}
        </template>
        <template #value>
          <FiatDisplay
            :value="thresholdValue"
            class="inline-flex"
            no-scramble
          />
        </template>
      </i18n-t>
    </div>

    <UnmatchedCards
      v-if="isPinned"
      v-model:selected="selected"
      :rows="visibleRows"
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
      :rows="visibleRows"
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
