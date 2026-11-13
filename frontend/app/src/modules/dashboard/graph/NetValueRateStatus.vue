<script setup lang="ts">
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import MissingDailyPrices from '@/modules/statistics/MissingDailyPrices.vue';
import { useSnapshotRateStatus } from '@/modules/statistics/pricing/use-snapshot-rate-status';

const { t } = useI18n({ useScope: 'global' });

const { status } = useSnapshotRateStatus();
const { failedDailyPrices } = useHistoricPriceCache();

const addingRates = ref<boolean>(false);

/** The dialog lists the days the backend reported no USD rate for, so it needs that report. */
const canAddRates = computed<boolean>(() => get(failedDailyPrices)[CURRENCY_USD] !== undefined);
</script>

<template>
  <div
    v-if="status.pending > 0 || status.unavailable > 0"
    class="flex flex-col gap-1 px-2 text-xs text-rui-text-secondary"
    data-testid="net-value-rate-status"
  >
    <p
      v-if="status.rateLimited"
      data-testid="net-value-rate-status-rate-limited"
    >
      {{ t('net_value_rate_status.rate_limited') }}
    </p>
    <p
      v-else-if="status.pending > 0"
      data-testid="net-value-rate-status-pending"
    >
      {{ t('net_value_rate_status.pending', { count: status.pending }, status.pending) }}
    </p>
    <div
      v-if="status.unavailable > 0"
      class="flex flex-wrap items-center gap-x-2"
      data-testid="net-value-rate-status-unavailable"
    >
      <span>{{ t('net_value_rate_status.unavailable', { count: status.unavailable }, status.unavailable) }}</span>
      <RuiButton
        v-if="canAddRates"
        size="sm"
        variant="text"
        color="primary"
        class="-my-1 px-1!"
        data-testid="net-value-rate-status-add"
        @click="addingRates = true"
      >
        {{ t('net_value_rate_status.add_rates') }}
      </RuiButton>
    </div>
    <RuiDialog
      v-model="addingRates"
      max-width="600"
    >
      <MissingDailyPrices
        v-if="addingRates && canAddRates"
        :asset="CURRENCY_USD"
        @close="addingRates = false"
      />
    </RuiDialog>
  </div>
</template>
