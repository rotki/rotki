<script setup lang="ts">
import { type BigNumber, Zero } from '@rotki/common';
import { AssetAmountDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { useWrappedFormatters } from '../use-wrapped-formatters';
import WrappedHighlight from './WrappedHighlight.vue';

interface TopDay {
  timestamp: number;
  amount: BigNumber;
}

/**
 * The period's headline figures, read before the lists that break them down. From `md` up each is
 * a card of its own; on a phone they share one card, a row each, as the staking totals do.
 */
const { ethOnGas, topDays, trades, transactions } = defineProps<{
  ethOnGas?: BigNumber;
  transactions?: Record<string, BigNumber>;
  trades?: Record<string, BigNumber>;
  topDays?: TopDay[];
}>();

const { t } = useI18n({ useScope: 'global' });
const { formatShortDate } = useWrappedFormatters();

function total(counts: Record<string, BigNumber> | undefined): BigNumber {
  return Object.values(counts ?? {}).reduce((acc, value) => acc.plus(value), Zero);
}

// every figure shows, zero included, so a quiet period reads as such and the row keeps its shape
const transactionCount = computed<BigNumber>(() => total(transactions));

const tradeCount = computed<BigNumber>(() => total(trades));

const busiestDay = computed<TopDay | undefined>(() =>
  topDays?.reduce<TopDay | undefined>((top, day) => (!top || day.amount.gt(top.amount) ? day : top), undefined));
</script>

<template>
  <div
    class="grid gap-4 md:grid-cols-2 lg:grid-cols-4 max-md:gap-0 max-md:rounded-rui-card max-md:border max-md:border-rui-divider max-md:bg-rui-surface"
    data-testid="wrapped-highlights"
  >
    <WrappedHighlight :label="t('wrapped.highlights.gas')">
      <AssetAmountDisplay
        asset="ETH"
        :amount="ethOnGas ?? Zero"
      />
    </WrappedHighlight>
    <WrappedHighlight :label="t('wrapped.highlights.transactions')">
      <ValueDisplay
        :value="transactionCount"
        :format="{ integer: true }"
      />
    </WrappedHighlight>
    <WrappedHighlight :label="t('wrapped.highlights.trades')">
      <ValueDisplay
        :value="tradeCount"
        :format="{ integer: true }"
      />
    </WrappedHighlight>
    <WrappedHighlight :label="t('wrapped.highlights.busiest_day')">
      <template v-if="busiestDay">
        {{ formatShortDate(busiestDay.timestamp) }}
      </template>
      <template v-else>
        -
      </template>
      <template
        v-if="busiestDay"
        #detail
      >
        <ValueDisplay
          :value="busiestDay.amount"
          :format="{ integer: true }"
        />
        {{ t('wrapped.unit.transactions', busiestDay.amount.toNumber()) }}
      </template>
    </WrappedHighlight>
  </div>
</template>
