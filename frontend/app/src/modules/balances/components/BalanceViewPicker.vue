<script setup lang="ts">
import { startPromise } from '@shared/utils';
import BalanceViewPanel from '@/modules/balances/components/BalanceViewPanel.vue';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { useBalanceView } from '@/modules/balances/view/use-balance-view';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { useBucketReconciliation } from '@/modules/history/reconciliation/use-bucket-reconciliation';

const { t } = useI18n({ useScope: 'global' });

const { available, isHistory } = useBalanceView();
const { error, processingRequired, stale } = storeToRefs(useHistoricalSnapshotStore());
const reconciliation = isAccountingUpdateEnabled() ? useBucketReconciliation() : undefined;

/** History disagrees with the queried balances somewhere, or is behind recent event edits. */
const needsAttention = computed<boolean>(() =>
  (reconciliation ? get(reconciliation.attention) > 0 : false) || get(processingRequired) || get(stale));

/** The reconciliation summary feeds the attention dot, so it loads once the picker is offered. */
function loadSummaryWhenAvailable(isAvailable: boolean): void {
  if (isAvailable && reconciliation)
    startPromise(reconciliation.ensureSummary());
}

watch(available, loadSummaryWhenAvailable, { immediate: true });
</script>

<template>
  <RuiMenu
    v-if="available"
    :options="{ placement: 'bottom-start' }"
    data-testid="balance-view-picker"
  >
    <template #activator="{ attrs }">
      <button
        type="button"
        class="inline-flex items-center gap-1 h-7 px-1.5 rounded-md text-sm text-rui-primary hover:bg-rui-primary/10"
        :aria-label="t('balance_view.label')"
        data-testid="balance-view-picker-trigger"
        v-bind="attrs"
      >
        <span class="grid">
          <span
            class="col-start-1 row-start-1"
            :class="{ invisible: isHistory }"
          >
            {{ t('balance_view.queried') }}
          </span>
          <span
            class="col-start-1 row-start-1"
            :class="{ invisible: !isHistory }"
          >
            {{ t('balance_view.history') }}
          </span>
        </span>
        <span
          class="size-1.5 rounded-full"
          :class="[
            error ? 'bg-rui-error' : 'bg-rui-warning',
            { invisible: !error && !needsAttention },
          ]"
          role="img"
          :aria-hidden="!error && !needsAttention"
          :aria-label="t('balance_view.attention')"
          data-testid="balance-view-attention"
        />
        <RuiIcon
          name="lu-chevron-down"
          size="14"
        />
      </button>
    </template>
    <BalanceViewPanel />
  </RuiMenu>
</template>
