<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { PriceStatus } from '@/modules/statistics/historical-balances/use-historical-balance-values';

/**
 * One fiat cell of the historical balances table, in whichever state its price is in.
 *
 * @remarks
 * Only the cell with `explain` says why there is no figure, so a row reads "Spam" once rather than
 * in every column.
 */
const { explain = false, priceAsset, status, value } = defineProps<{
  value: BigNumber | undefined;
  status: PriceStatus;
  /** Name the reason when there is no figure, instead of a dash. */
  explain?: boolean;
  priceAsset?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <FiatDisplay
    v-if="status === PriceStatus.PRICED || status === PriceStatus.PENDING"
    :value="value"
    :loading="status === PriceStatus.PENDING"
    :price-asset="priceAsset"
  />
  <RuiTooltip
    v-else-if="explain"
    :open-delay="400"
    :class-names="{ tooltip: 'max-w-[16rem]' }"
  >
    <template #activator>
      <RuiChip
        v-if="status === PriceStatus.SPAM"
        size="sm"
        color="warning"
        data-testid="historical-balances-spam"
      >
        {{ t('historical_balances.price.spam') }}
      </RuiChip>
      <span
        v-else
        class="text-rui-text-secondary"
        data-testid="historical-balances-no-price"
      >
        {{ t('historical_balances.price.missing') }}
      </span>
    </template>
    {{ status === PriceStatus.SPAM ? t('historical_balances.price.spam_hint') : t('historical_balances.price.missing_hint') }}
  </RuiTooltip>
  <span
    v-else
    class="text-rui-text-secondary"
  >
    -
  </span>
</template>
