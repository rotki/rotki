<script setup lang="ts">
import { msg } from '@/message-key';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import BinanceSavingDetail from '@/modules/balances/exchanges/BinanceSavingDetail.vue';
import ExchangeBalanceCards from '@/modules/balances/exchanges/ExchangeBalanceCards.vue';
import ExchangeBalancesEmpty from '@/modules/balances/exchanges/ExchangeBalancesEmpty.vue';
import ExchangeBalancesRefreshButton from '@/modules/balances/exchanges/ExchangeBalancesRefreshButton.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
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
  modelView,
  navigateToExchangeSetup,
  refreshExchangeBalances,
  refreshInView,
  refreshSelectedExchangeBalances,
  sortedExchanges,
  totalBalance,
} = useExchangeBalancesPage(() => exchange);

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

      <!-- a frame rather than a card, so the table's pagination bar sticks to the page -->
      <TableFrame>
        <template #toolbar>
          <!-- Binance also keeps savings, whose interest history shares the table's place -->
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
          <!-- on the right, as the dashboard's tables keep their search -->
          <RuiTextField
            v-if="modelView === 'balances'"
            v-model="search"
            variant="outlined"
            color="primary"
            dense
            prepend-icon="lu-search"
            :placeholder="t('common.actions.search')"
            :aria-label="t('common.actions.search')"
            class="ml-auto w-full max-w-64 [&_input]:py-1.5! [&_input]:text-sm! [&_input]:leading-5! [&_input::placeholder]:opacity-100! [&_input::placeholder]:text-rui-text-secondary! [&_svg]:size-4!"
            hide-details
            clearable
            data-testid="exchange-balances-search"
            @click:clear="search = ''"
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
          :loading="isExchangeLoading && balances.length === 0"
          :balances="balances"
          :show-per-protocol="!exchange"
          sticky-header
        >
          <template #empty>
            <TableEmptyNotice
              icon="lu-coins-exchange"
              :title="t('exchange_balances.empty_table.title')"
              :description="t('exchange_balances.empty_table.description')"
            />
          </template>
        </AssetBalances>
      </TableFrame>
    </template>
  </TablePageLayout>
</template>
