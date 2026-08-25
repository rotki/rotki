<script setup lang="ts">
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
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
  confirmFixDuplicate,
  duplicateChangesMessage,
  duplicateChipText,
  fixLoading,
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
</script>

<template>
  <div>
    <div
      v-if="showMissingAcquisition"
      class="pb-4"
    >
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
      class="pb-4"
      :popper="{ placement: 'bottom' }"
      :open-delay="400"
      tooltip-class="max-w-80"
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
      class="pb-4"
      :popper="{ placement: 'bottom' }"
      :open-delay="400"
      tooltip-class="max-w-80"
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

    <div
      v-if="showDuplicates"
      class="pb-4"
    >
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

          <RuiButton
            v-if="isAutoFixable && !hasDuplicateChanges"
            size="sm"
            variant="text"
            class="!py-0 underline !text-xs gap-1"
            color="primary"
            :loading="fixLoading"
            data-testid="duplicate-fix-all"
            @click="confirmFixDuplicate()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-wand-sparkles"
                size="10"
              />
            </template>
            {{ t('customized_event_duplicates.actions.fix_all_shown') }}
          </RuiButton>
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
          size="sm"
          variant="text"
          color="secondary"
          class="!py-0 underline"
          data-testid="duplicate-refresh"
          @click="refreshDuplicateView()"
        >
          {{ allDuplicatesResolved ? t('customized_event_duplicates.chips.clear_filter') : t('common.refresh') }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
