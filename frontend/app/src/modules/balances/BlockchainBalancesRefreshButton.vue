<script setup lang="ts">
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import BlockchainBalanceRefreshBehaviourMenu from '@/modules/balances/BlockchainBalanceRefreshBehaviourMenu.vue';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';

const { t } = useI18n({ useScope: 'global' });

const menuOpen = ref<boolean>(false);

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

async function refreshOnlyPrices(): Promise<void> {
  set(menuOpen, false);
  await refreshPrices(true);
}
</script>

<template>
  <!--
    One Refresh for the page: balances on every chain, then prices. The menu keeps a prices-only
    refresh and the choice of whether Refresh also re-detects tokens.
  -->
  <RuiButtonGroup
    variant="outlined"
    color="primary"
  >
    <RuiButton
      data-testid="blockchain-balances-refresh"
      :disabled="refreshDisabled"
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
            'data-testid': 'blockchain-balances-refresh-menu',
          }"
          color="primary"
          variant="outlined"
          class="outline-0! px-2"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>

      <div class="w-80 max-w-full py-1">
        <RuiButton
          variant="list"
          :disabled="pricesDisabled"
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
            <span>{{ t('blockchain_balances.refresh_menu.prices') }}</span>
            <span class="text-caption font-normal text-rui-text-secondary whitespace-normal">
              {{ t('blockchain_balances.refresh_menu.prices_description') }}
            </span>
          </span>
        </RuiButton>
        <RuiDivider class="my-1" />
        <BlockchainBalanceRefreshBehaviourMenu />
      </div>
    </RuiMenu>
  </RuiButtonGroup>
</template>
