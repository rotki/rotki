<script lang="ts" setup>
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import SummaryCard from '@/modules/dashboard/summary/SummaryCard.vue';
import SummaryCardCreateButton from '@/modules/dashboard/summary/SummaryCardCreateButton.vue';
import ExchangeBox from './ExchangeBox.vue';

const { t } = useI18n({ useScope: 'global' });

const { exchanges } = useExchangeData();
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.exchange_balances.title')"
      :navigates-to="{ name: '/balances/exchange/[[exchange]]' }"
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
