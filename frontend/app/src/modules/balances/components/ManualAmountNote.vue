<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { AssetAmountDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';

const { amount, asset } = defineProps<{
  amount: BigNumber;
  /** When provided, formats with the asset's symbol; otherwise renders a unitless amount. */
  asset?: string;
}>();
</script>

<template>
  <i18n-t
    scope="global"
    keypath="balance_view.manual_amount"
    tag="span"
  >
    <template #amount>
      <AssetAmountDisplay
        v-if="asset"
        class="inline"
        :amount="amount"
        :asset="asset"
        no-truncate
      />
      <ValueDisplay
        v-else
        class="inline"
        :value="amount"
        :format="{ noRoundingMark: true }"
      />
    </template>
  </i18n-t>
</template>
