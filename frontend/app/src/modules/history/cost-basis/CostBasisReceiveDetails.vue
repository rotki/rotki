<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { CostBasisReceive } from '@/modules/history/cost-basis/types';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { COST_BASIS_FIAT_FORMAT } from '@/modules/history/cost-basis/cost-basis-helpers';
import CostBasisBucketLabel from '@/modules/history/cost-basis/CostBasisBucketLabel.vue';

const { entry, amount } = defineProps<{
  entry: CostBasisReceive;
  amount?: BigNumber;
}>();

const { t } = useI18n({ useScope: 'global' });

const costValue = computed<BigNumber | undefined>(() => amount ? entry.basisPerUnit.multipliedBy(amount) : undefined);

/** Where the basis comes from, in words. An unknown source is shown as the backend names it. */
const source = computed<string>(() => {
  switch (entry.basisSource) {
    case 'event_amount':
      return t('cost_basis_overlay.source.event_amount');
    case 'price_oracle':
      return t('cost_basis_overlay.source.price_oracle');
    case 'transfer_in':
      return t('cost_basis_overlay.source.transfer_in');
    case 'zero_cost':
      return t('cost_basis_overlay.source.zero_cost');
    case 'free_acquisition':
      return t('cost_basis_overlay.source.free_acquisition');
    default:
      return entry.basisSource;
  }
});
</script>

<template>
  <div
    class="flex flex-col gap-3 min-w-80"
    data-testid="cost-basis-receive"
  >
    <CostBasisBucketLabel
      :location="entry.location"
      :location-label="entry.locationLabel"
      :protocol="entry.protocol"
    />
    <div class="flex flex-col gap-1 text-sm">
      <div class="flex items-center justify-between gap-6">
        <span class="text-rui-text-secondary">{{ t('cost_basis_overlay.cost_basis') }}</span>
        <FiatDisplay
          :value="entry.basisPerUnit"
          :format="COST_BASIS_FIAT_FORMAT"
          class="font-medium tabular-nums"
          data-testid="cost-basis-per-unit"
        />
      </div>
      <div
        v-if="costValue"
        class="flex items-center justify-between gap-6"
      >
        <span class="text-rui-text-secondary">{{ t('cost_basis_overlay.cost_value') }}</span>
        <FiatDisplay
          :value="costValue"
          :format="COST_BASIS_FIAT_FORMAT"
          class="font-medium tabular-nums"
          data-testid="cost-basis-cost-value"
        />
      </div>
      <span
        class="text-xs text-rui-text-secondary max-w-80"
        data-testid="cost-basis-source"
      >
        {{ source }}
      </span>
    </div>
  </div>
</template>
