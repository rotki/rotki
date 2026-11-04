<script setup lang="ts">
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import RefreshSplitButton from '@/modules/shell/components/RefreshSplitButton.vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const { t } = useI18n({ useScope: 'global' });

const { fetchManualBalances } = useManualBalances();
const { refreshing: refreshingPrices, refreshPrices } = usePriceRefresh();
const { useIsActive } = useTaskCenter();
const refreshingBalances = useIsActive(ActivityKind.MANUAL_BALANCES);

const loading = logicOr(refreshingBalances, refreshingPrices);

async function refresh(): Promise<void> {
  await fetchManualBalances(true);
  await refreshPrices(true);
}

async function refreshOnlyPrices(close: () => void): Promise<void> {
  close();
  await refreshPrices(true);
}
</script>

<template>
  <RefreshSplitButton
    test-id="manual-balances-refresh"
    :menu-label="t('manual_balances.refresh_menu.label')"
    :loading="loading"
    @refresh="refresh()"
  >
    <template #default="{ close }">
      <div class="w-80 max-w-full py-1">
        <RuiButton
          variant="list"
          :disabled="refreshingPrices"
          data-testid="price-refresh"
          @click="refreshOnlyPrices(close)"
        >
          <template #prepend>
            <RuiIcon
              size="18"
              name="lu-chart-line"
            />
          </template>
          <span class="flex flex-col items-start text-left">
            <span>{{ t('manual_balances.refresh_menu.prices') }}</span>
            <span class="text-caption font-normal text-rui-text-secondary whitespace-normal">
              {{ t('manual_balances.refresh_menu.prices_description') }}
            </span>
          </span>
        </RuiButton>
      </div>
    </template>
  </RefreshSplitButton>
</template>
