<script setup lang="ts">
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import BlockchainBalanceRefreshBehaviourMenu from '@/modules/balances/BlockchainBalanceRefreshBehaviourMenu.vue';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import RefreshSplitButton from '@/modules/shell/components/RefreshSplitButton.vue';

const { t } = useI18n({ useScope: 'global' });

const { isRefreshing } = useBalanceStatus();
const { isDetectingTokens, refreshDisabled } = useBlockchainAccountLoading();
const { refreshing: refreshingPrices, refreshPrices } = usePriceRefresh();
const { loadingBalances } = useBalancesLoading();
const { refreshBlockchainAndPrices } = useBalanceRefresh();

const loading = logicOr(isDetectingTokens, isRefreshing, refreshingPrices);
const pricesDisabled = logicOr(refreshingPrices, loadingBalances);

async function refresh(): Promise<void> {
  await refreshBlockchainAndPrices();
}

async function refreshOnlyPrices(close: () => void): Promise<void> {
  close();
  await refreshPrices(true);
}
</script>

<template>
  <RefreshSplitButton
    test-id="blockchain-balances-refresh"
    :menu-label="t('blockchain_balances.refresh_menu.label')"
    :loading="loading"
    :disabled="refreshDisabled"
    @refresh="refresh()"
  >
    <template #default="{ close }">
      <div class="w-80 max-w-full py-1">
        <RuiButton
          variant="list"
          :disabled="pricesDisabled"
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
            <span>{{ t('blockchain_balances.refresh_menu.prices') }}</span>
            <span class="text-caption font-normal text-rui-text-secondary whitespace-normal">
              {{ t('blockchain_balances.refresh_menu.prices_description') }}
            </span>
          </span>
        </RuiButton>
        <RuiDivider class="my-1" />
        <BlockchainBalanceRefreshBehaviourMenu />
      </div>
    </template>
  </RefreshSplitButton>
</template>
