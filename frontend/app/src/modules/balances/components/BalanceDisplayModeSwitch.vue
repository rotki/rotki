<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { startPromise } from '@shared/utils';
import { type BalanceDisplayMode, useBalanceDisplayModeStore } from '@/modules/balances/use-balance-display-mode-store';
import { useCurrentHistoricalBalances } from '@/modules/balances/use-current-historical-balances';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { useBucketReconciliation } from '@/modules/history/reconciliation/use-bucket-reconciliation';

const { compact = false } = defineProps<{ compact?: boolean }>();

const enabled = isAccountingUpdateEnabled();

const store = useBalanceDisplayModeStore();
const { mode, isHistoryMode, processingRequired, stale, loading } = storeToRefs(store);

// A disabled build instantiates none of the history machinery and fetches nothing.
const controller = enabled ? useCurrentHistoricalBalances() : undefined;
const reconciliation = enabled ? useBucketReconciliation() : undefined;

const { t } = useI18n({ useScope: 'global' });

if (reconciliation)
  startPromise(reconciliation.ensureSummary());

const attention = computed<number>(() => reconciliation ? get(reconciliation.attention) : 0);

const needsProcessing = computed<boolean>(() => get(processingRequired) || get(stale));
const showNotice = computed<boolean>(() => get(isHistoryMode) && get(needsProcessing));
const showAttention = computed<boolean>(() => get(attention) > 0 || get(needsProcessing));

const reconciliationLink: RouteLocationRaw = {
  name: '/history/data-issues/[[tab]]',
  params: { tab: 'reconciliation' },
};

function setMode(value: BalanceDisplayMode | BalanceDisplayMode[] | undefined): void {
  const next = Array.isArray(value) ? value[0] : value;
  if (next === 'queried' || next === 'history')
    store.setMode(next);
}

function processNow(): void {
  if (controller)
    startPromise(controller.triggerProcessing());
}
</script>

<template>
  <div
    v-if="enabled"
    class="flex flex-col gap-1"
    data-testid="balance-display-mode-switch"
  >
    <div class="relative flex items-center gap-2">
      <RuiTooltip
        class="inline-flex"
        :options="{ placement: 'top' }"
        :open-delay="400"
        :class-names="{ tooltip: 'max-w-80' }"
      >
        <template #activator>
          <RuiButtonGroup
            :model-value="mode"
            variant="segmented"
            required
            size="sm"
            :aria-label="t('balance_display_mode.label')"
            data-testid="balance-display-mode-group"
            @update:model-value="setMode($event)"
          >
            <RuiButton model-value="queried">
              {{ t('balance_display_mode.queried') }}
            </RuiButton>
            <RuiButton model-value="history">
              {{ t('balance_display_mode.history') }}
            </RuiButton>
          </RuiButtonGroup>
        </template>
        <p>{{ t('balance_display_mode.queried_tooltip') }}</p>
        <p>{{ t('balance_display_mode.history_tooltip') }}</p>
      </RuiTooltip>
      <RuiTooltip
        v-if="showAttention"
        :class="compact ? 'absolute -right-1 -top-1' : 'inline-flex'"
        :options="{ placement: 'top' }"
        :open-delay="400"
        :class-names="{ tooltip: 'max-w-80' }"
      >
        <template #activator>
          <span
            v-if="compact"
            class="block size-3 rounded-full bg-rui-warning"
            role="img"
            :aria-label="t('balance_display_mode.attention')"
            data-testid="balance-display-mode-attention"
          />
          <RuiChip
            v-else
            color="warning"
            variant="tonal"
            size="sm"
            data-testid="balance-display-mode-attention"
          >
            {{ t('balance_display_mode.attention') }}
          </RuiChip>
        </template>
        {{ t('balance_display_mode.attention_tooltip') }}
      </RuiTooltip>
    </div>

    <RuiAlert
      v-if="showNotice"
      type="warning"
      data-testid="balance-display-mode-notice"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span>{{ t('balance_display_mode.stale_notice') }}</span>
        <RuiButton
          size="sm"
          color="primary"
          :loading="loading"
          data-testid="balance-display-mode-process"
          @click="processNow()"
        >
          {{ t('balance_display_mode.process_now') }}
        </RuiButton>
        <RouterLink
          :to="reconciliationLink"
          data-testid="balance-display-mode-reconciliation-link"
        >
          {{ t('balance_display_mode.reconciliation') }}
        </RouterLink>
      </div>
    </RuiAlert>
  </div>
</template>
