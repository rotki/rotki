<script setup lang="ts">
import { type AssetBalanceWithPrice, toHumanReadable, toSentenceCase } from '@rotki/common';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import BinanceSavingDetail from '@/modules/balances/exchanges/BinanceSavingDetail.vue';

const tab = defineModel<number>({ required: true });

const { exchange, loading = false } = defineProps<{
  exchange: string;
  loading?: boolean;
  balances: AssetBalanceWithPrice[];
}>();

const emit = defineEmits<{
  refresh: [exchange: string];
}>();

const { t } = useI18n({ useScope: 'global' });

function isBinance(exchange?: string): exchange is 'binance' | 'binanceus' {
  return !!exchange && ['binance', 'binanceus'].includes(exchange);
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between gap-4 mb-2">
      <RuiTabs
        v-model="tab"
        color="primary"
      >
        <RuiTab>{{ t('exchange_balances.tabs.balances') }}</RuiTab>
        <RuiTab v-if="isBinance(exchange)">
          {{ t('exchange_balances.tabs.savings_interest_history') }}
        </RuiTab>
      </RuiTabs>

      <RuiButton
        color="primary"
        variant="outlined"
        class="shrink-0"
        :disabled="tab !== 0"
        :loading="loading"
        @click="emit('refresh', exchange)"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('dashboard.exchange_balances.refresh', { exchange: toSentenceCase(toHumanReadable(exchange)) }) }}
      </RuiButton>
    </div>

    <RuiDivider />

    <RuiTabItems v-model="tab">
      <RuiTabItem class="pt-4 md:pl-4">
        <AssetBalances
          :breakdown="{ hide: true }"
          :loading="loading"
          :balances="balances"
          sticky-header
        />
      </RuiTabItem>
      <RuiTabItem
        v-if="isBinance(exchange)"
        class="md:pl-4"
      >
        <BinanceSavingDetail :exchange="exchange" />
      </RuiTabItem>
    </RuiTabItems>
  </div>
</template>
