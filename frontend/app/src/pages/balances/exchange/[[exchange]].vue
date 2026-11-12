<script setup lang="ts">
import { type AssetBalanceWithPrice, type BigNumber, Zero } from '@rotki/common';
import { msg } from '@/message-key';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import BinanceSavingDetail from '@/modules/balances/exchanges/BinanceSavingDetail.vue';
import ExchangeAccountPicker from '@/modules/balances/exchanges/ExchangeAccountPicker.vue';
import ExchangeBalanceCards from '@/modules/balances/exchanges/ExchangeBalanceCards.vue';
import ExchangeBalancesEmpty from '@/modules/balances/exchanges/ExchangeBalancesEmpty.vue';
import ExchangeBalancesRefreshButton from '@/modules/balances/exchanges/ExchangeBalancesRefreshButton.vue';
import { useExchangeAccountSelection } from '@/modules/balances/exchanges/use-exchange-account-selection';
import { NoteLocation } from '@/modules/core/common/notes';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import TableSearchField from '@/modules/core/table/TableSearchField.vue';
import HideSmallBalances from '@/modules/settings/HideSmallBalances.vue';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { isBinance, useExchangeBalancesPage } from '@/pages/balances/exchange/use-exchange-balances-page';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.exchange_balances'), icon: 'lu-coins-exchange', parent: '/balances/', order: 20, drawer: 'balances-exchange' },
    noteLocation: NoteLocation.BALANCES_EXCHANGE,
  },
  props: true,
});

const { exchange } = defineProps<{ exchange?: string }>();

const { t } = useI18n({ useScope: 'global' });

const search = ref<string>('');

const {
  balances,
  exchangeBalance,
  isExchangeLoading,
  lastRefreshFailed,
  modelView,
  navigateToExchangeSetup,
  refreshExchangeBalances,
  refreshInView,
  refreshSelectedExchangeBalances,
  sortedExchanges,
  totalBalance,
} = useExchangeBalancesPage(() => exchange);

const { accountBalances, accounts, modelAccount, picked } = useExchangeAccountSelection(() => exchange);

const shownBalances = computed<AssetBalanceWithPrice[]>(() => get(accountBalances) ?? get(balances));

/** With one account picked, its empty table is unknown when its own refresh failed or none has loaded it. */
const shownRefreshFailed = computed<boolean>(() => {
  const account = get(picked);
  return account ? account.error !== undefined || !account.loaded : get(lastRefreshFailed);
});

/** The whole exchange's total, as its card shows it, for the picker's all accounts option. */
const exchangeTotal = computed<BigNumber>(() => (exchange ? exchangeBalance(exchange) : Zero));

const binance = computed<'binance' | 'binanceus' | undefined>(() => (isBinance(exchange) ? exchange : undefined));
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.exchange_balances')]">
    <template #buttons>
      <ExchangeBalancesRefreshButton
        :exchanges="sortedExchanges"
        :selected="exchange"
        :loading="isExchangeLoading"
        @refresh="refreshInView()"
        @refresh-all="refreshExchangeBalances()"
        @refresh-exchange="refreshSelectedExchangeBalances($event)"
      />
      <RuiButton
        color="primary"
        data-testid="add-exchange"
        @click="navigateToExchangeSetup()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('exchange_balances.add_exchange') }}
      </RuiButton>
      <HideSmallBalances :source="BalanceSource.EXCHANGES" />
    </template>

    <ExchangeBalancesEmpty
      v-if="sortedExchanges.length === 0"
      @connect="navigateToExchangeSetup($event)"
    />

    <template v-else>
      <ExchangeBalanceCards
        :exchanges="sortedExchanges"
        :selected="exchange"
        :total="totalBalance"
        :exchange-balance="exchangeBalance"
      />

      <TableFrame>
        <template #toolbar>
          <RuiButtonGroup
            v-if="binance"
            v-model="modelView"
            variant="segmented"
            required
            data-testid="exchange-balances-view"
          >
            <RuiButton model-value="balances">
              {{ t('exchange_balances.tabs.balances') }}
            </RuiButton>
            <RuiButton model-value="savings">
              {{ t('exchange_balances.tabs.savings_interest_history') }}
            </RuiButton>
          </RuiButtonGroup>
          <ExchangeAccountPicker
            v-if="modelView === 'balances' && accounts.length > 0"
            v-model="modelAccount"
            :accounts="accounts"
            :total="exchangeTotal"
          />
          <TableSearchField
            v-if="modelView === 'balances'"
            v-model="search"
            data-testid="exchange-balances-search"
          />
        </template>

        <BinanceSavingDetail
          v-if="binance && modelView === 'savings'"
          class="p-4"
          :exchange="binance"
        />
        <AssetBalances
          v-else
          v-model:search="search"
          data-testid="exchange-asset-balances"
          :breakdown="{ hide: true }"
          :loading="isExchangeLoading && shownBalances.length === 0"
          :balances="shownBalances"
          :display="{ showPerProtocol: !exchange, stickyHeader: true }"
        >
          <template #empty>
            <TableEmptyNotice
              v-if="shownRefreshFailed"
              icon="lu-circle-alert"
              :title="t('exchange_balances.empty_table.failed_title')"
              :description="t('exchange_balances.empty_table.failed_description')"
              data-testid="exchange-balances-refresh-failed"
            />
            <TableEmptyNotice
              v-else
              icon="lu-coins-exchange"
              :title="t('exchange_balances.empty_table.title')"
              :description="t('exchange_balances.empty_table.description')"
              data-testid="exchange-balances-empty"
            />
          </template>
        </AssetBalances>
      </TableFrame>
    </template>
  </TablePageLayout>
</template>
