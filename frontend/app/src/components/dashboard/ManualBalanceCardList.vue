<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { toSentenceCase } from '@/utils/text';
import { Routes } from '@/router/routes';

defineProps<{
  name: string;
  amount: BigNumber;
}>();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const manualBalancesRoute = Routes.ACCOUNTS_BALANCES_MANUAL;
</script>

<template>
  <VListItem
    :id="`${name}_box`"
    :ripple="false"
    :data-cy="`manual-balance-box__item__${name}`"
    class="manual-balance-box__item min-h-[2.25rem] group"
    :to="manualBalancesRoute"
  >
    <VListItemAvatar tile class="grayscale group-hover:grayscale-0 m-0 mr-1">
      <LocationDisplay :identifier="name" icon />
    </VListItemAvatar>
    <VListItemContent>
      <div class="flex flex-wrap justify-between gap-2">
        <span>
          {{ toSentenceCase(name) }}
        </span>
        <AmountDisplay
          show-currency="symbol"
          :fiat-currency="currencySymbol"
          :value="amount"
        />
      </div>
    </VListItemContent>
  </VListItem>
</template>
