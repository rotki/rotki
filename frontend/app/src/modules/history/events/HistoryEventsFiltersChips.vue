<script setup lang="ts">
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { startPromise } from '@shared/utils';
import HistoryEventsDuplicateFixAll from '@/modules/history/events/HistoryEventsDuplicateFixAll.vue';
import { useHistoryEventsFiltersChips } from '@/modules/history/events/use-history-events-filters-chips';

const { groupIdentifiers, duplicateHandlingStatus } = defineProps<{
  groupIdentifiers?: string[];
  duplicateHandlingStatus?: DuplicateHandlingStatus;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  allDuplicatesResolved,
  duplicateChangesMessage,
  duplicateChipText,
  fixLoading,
  fixQuestion,
  fixShownDuplicates,
  hasDuplicateChanges,
  isAutoFixable,
  refreshDuplicateView,
  removeAccountingEventParam,
  removeDuplicateEventsParam,
  removeMissingAcquisitionParam,
  removeNegativeBalanceParam,
  showAccountingEvent,
  showDuplicates,
  showMissingAcquisition,
  showNegativeBalance,
} = useHistoryEventsFiltersChips({
  duplicateHandlingStatus: () => duplicateHandlingStatus,
  groupIdentifiers: () => groupIdentifiers,
  onRefresh: () => emit('refresh'),
});

/** Renders nothing without a chip, so the strip it sits in can collapse. */
const anyChip = computed<boolean>(() =>
  get(showMissingAcquisition) || get(showNegativeBalance) || get(showAccountingEvent) || get(showDuplicates));
</script>

<template>
  <div
    v-if="anyChip"
    class="flex flex-wrap items-start gap-2"
  >
    <div v-if="showMissingAcquisition">
      <RuiChip
        closeable
        color="primary"
        size="sm"
        variant="outlined"
        data-testid="missing-acquisition-chip"
        @click:close="removeMissingAcquisitionParam()"
      >
        {{ t('transactions.events.show_missing_acquisition') }}
      </RuiChip>
    </div>

    <RuiTooltip
      v-if="showNegativeBalance"
      :options="{ placement: 'bottom' }"
      :open-delay="400"
      :class-names="{ tooltip: 'max-w-80' }"
    >
      <template #activator>
        <RuiChip
          closeable
          color="error"
          size="sm"
          variant="outlined"
          data-testid="negative-balance-chip"
          @click:close="removeNegativeBalanceParam()"
        >
          {{ t('transactions.events.show_negative_balance') }}
        </RuiChip>
      </template>
      {{ t('historical_balances.negative_balances.view_event_tooltip') }}
    </RuiTooltip>

    <RuiTooltip
      v-if="showAccountingEvent"
      :options="{ placement: 'bottom' }"
      :open-delay="400"
      :class-names="{ tooltip: 'max-w-80' }"
    >
      <template #activator>
        <RuiChip
          closeable
          color="warning"
          size="sm"
          variant="outlined"
          data-testid="accounting-divergence-chip"
          @click:close="removeAccountingEventParam()"
        >
          {{ t('transactions.events.show_accounting_divergence') }}
        </RuiChip>
      </template>
      {{ t('transactions.events.show_accounting_divergence_tooltip') }}
    </RuiTooltip>

    <div v-if="showDuplicates">
      <RuiChip
        closeable
        color="warning"
        size="sm"
        variant="outlined"
        data-testid="duplicate-events-chip"
        @click:close="removeDuplicateEventsParam()"
      >
        <div class="flex gap-1">
          {{ duplicateChipText }}

          <HistoryEventsDuplicateFixAll
            v-if="isAutoFixable && !hasDuplicateChanges"
            :question="fixQuestion"
            :loading="fixLoading"
            @confirm="startPromise(fixShownDuplicates())"
          />
        </div>
      </RuiChip>

      <div
        v-if="hasDuplicateChanges"
        class="mt-1 flex items-center gap-1 text-xs text-rui-secondary"
        data-testid="duplicate-changes"
      >
        <RuiIcon
          name="lu-info"
          size="16"
        />
        <span>{{ duplicateChangesMessage }}</span>
        <RuiButton
          variant="link"
          color="secondary"
          class="underline"
          data-testid="duplicate-refresh"
          @click="refreshDuplicateView()"
        >
          {{ allDuplicatesResolved ? t('customized_event_duplicates.chips.clear_filter') : t('common.refresh') }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
