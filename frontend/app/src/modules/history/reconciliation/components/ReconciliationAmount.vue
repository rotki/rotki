<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { useAmountDisplaySettings } from '@/modules/assets/amount-display';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';

const { amount, asset, signed = false } = defineProps<{
  amount: BigNumber | null;
  asset?: string;
  /** Show a leading `+` for a positive value, as for a balance difference. */
  signed?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { shouldShowAmount } = useAmountDisplaySettings();

const showPlus = computed<boolean>(() => signed && !!amount && amount.gt(0) && get(shouldShowAmount));
</script>

<template>
  <span
    v-if="amount === null"
    class="text-rui-text-disabled"
    :title="t('data_issues.reconciliation.not_available')"
    data-testid="reconciliation-amount-unavailable"
  >
    {{ t('data_issues.reconciliation.no_value') }}
  </span>
  <span
    v-else
    class="inline-flex items-baseline gap-0.5 tabular-nums"
  >
    <span v-if="showPlus">+</span>
    <AssetAmountDisplay
      :amount="amount"
      :asset="asset"
    />
  </span>
</template>
