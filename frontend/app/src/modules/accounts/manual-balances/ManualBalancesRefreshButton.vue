<script setup lang="ts">
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const { t } = useI18n({ useScope: 'global' });

const menuOpen = ref<boolean>(false);

const { fetchManualBalances } = useManualBalances();
const { refreshing: refreshingPrices, refreshPrices } = usePriceRefresh();
const { useIsActive } = useTaskCenter();
const refreshingBalances = useIsActive(ActivityKind.MANUAL_BALANCES);

const loading = logicOr(refreshingBalances, refreshingPrices);

async function refresh(): Promise<void> {
  await fetchManualBalances(true);
  await refreshPrices(true);
}

async function refreshOnlyPrices(): Promise<void> {
  set(menuOpen, false);
  await refreshPrices(true);
}
</script>

<template>
  <RuiButtonGroup
    variant="outlined"
    color="primary"
  >
    <RuiButton
      data-testid="manual-balances-refresh"
      :loading="loading"
      @click="refresh()"
    >
      <template #prepend>
        <RuiIcon name="lu-refresh-ccw" />
      </template>
      {{ t('common.refresh') }}
    </RuiButton>
    <RuiMenu
      v-model="menuOpen"
      :options="{ placement: 'bottom-end' }"
      :class-names="{ root: 'flex' }"
    >
      <template #activator="{ attrs }">
        <RuiButton
          v-bind="{
            ...attrs,
            'data-testid': 'manual-balances-refresh-menu',
          }"
          color="primary"
          variant="outlined"
          class="px-2"
          :aria-label="t('manual_balances.refresh_menu.label')"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>

      <div class="w-80 max-w-full py-1">
        <RuiButton
          variant="list"
          :disabled="refreshingPrices"
          data-testid="price-refresh"
          @click="refreshOnlyPrices()"
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
    </RuiMenu>
  </RuiButtonGroup>
</template>
