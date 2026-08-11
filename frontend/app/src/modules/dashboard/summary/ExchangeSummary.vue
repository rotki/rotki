<script lang="ts" setup>
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import SummaryCard from '@/modules/dashboard/summary/SummaryCard.vue';
import SummaryCardCreateButton from '@/modules/dashboard/summary/SummaryCardCreateButton.vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import ExchangeBox from './ExchangeBox.vue';

const { t } = useI18n({ useScope: 'global' });

const { useIsActive } = useTaskCenter();
const { refreshBalance } = useBalanceRefresh();
const { exchanges } = useExchangeData();

const isExchangeLoading = useIsActive(ActivityKind.EXCHANGE_BALANCES);
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.exchange_balances.title')"
      can-refresh
      :is-loading="isExchangeLoading"
      :navigates-to="{ name: '/balances/exchange/[[exchange]]' }"
      @refresh="refreshBalance($event)"
    >
      <SummaryCardCreateButton
        v-if="exchanges.length === 0"
        :to="{
          path: '/api-keys/exchanges',
          query: {
            add: 'true',
          },
        }"
      >
        {{ t('dashboard.exchange_balances.add') }}
      </SummaryCardCreateButton>
      <div
        v-else
        data-testid="exchange-balances"
      >
        <ExchangeBox
          v-for="exchange in exchanges"
          :key="exchange.location"
          :location="exchange.location"
          :amount="exchange.total"
        />
      </div>
    </SummaryCard>
  </div>
</template>
