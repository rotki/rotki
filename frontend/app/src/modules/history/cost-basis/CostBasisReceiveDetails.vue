<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { CostBasisReceive } from '@/modules/history/cost-basis/types';
import { RuiIcon } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
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
    class="flex flex-col gap-3"
    data-testid="cost-basis-receive"
  >
    <CostBasisBucketLabel
      :location="entry.location"
      :location-label="entry.locationLabel"
      :method="entry.method"
      :protocol="entry.protocol"
    />

    <dl class="grid grid-cols-[1fr_auto] items-baseline gap-x-4 gap-y-1 text-sm tabular-nums">
      <template v-if="costValue">
        <dt class="text-rui-text-secondary">
          {{ t('cost_basis_overlay.cost_value') }}
        </dt>
        <dd class="text-right font-semibold">
          <FiatDisplay
            :value="costValue"
            :format="COST_BASIS_FIAT_FORMAT"
            data-testid="cost-basis-cost-value"
          />
        </dd>
      </template>
      <dt
        class="text-rui-text-secondary"
        :class="{ 'pl-3 text-xs': costValue }"
      >
        {{ t('cost_basis_overlay.per_unit') }}
      </dt>
      <dd
        class="text-right"
        :class="{ 'text-xs text-rui-text-secondary': costValue }"
      >
        <FiatDisplay
          :value="entry.basisPerUnit"
          :format="COST_BASIS_FIAT_FORMAT"
          data-testid="cost-basis-per-unit"
        />
      </dd>
    </dl>

    <p class="flex gap-1.5 text-xs text-rui-text-secondary">
      <RuiIcon
        name="lu-info"
        size="12"
        class="shrink-0 mt-0.5"
      />
      <span data-testid="cost-basis-source">{{ source }}</span>
    </p>
  </div>
</template>
