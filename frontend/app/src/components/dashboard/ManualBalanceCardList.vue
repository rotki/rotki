<script setup lang="ts">
import { toSentenceCase } from '@/utils/text';
import { Routes } from '@/router/routes';
import type { BigNumber } from '@rotki/common';

defineProps<{
  name: string;
  amount: BigNumber;
}>();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const manualBalancesRoute = Routes.ACCOUNTS_BALANCES_MANUAL;
</script>

<template>
  <RouterLink :to="manualBalancesRoute">
    <ListItem
      data-cy="manual-balance__summary"
      class="group py-1 px-6"
      :data-location="name"
    >
      <template #avatar>
        <div class="grayscale group-hover:grayscale-0">
          <LocationDisplay
            :identifier="name"
            icon
            size="26px"
          />
        </div>
      </template>
      <div class="flex flex-wrap justify-between gap-1 text-rui-text">
        {{ toSentenceCase(name) }}
        <AmountDisplay
          show-currency="symbol"
          :fiat-currency="currencySymbol"
          :value="amount"
          class="font-medium"
        />
      </div>
    </ListItem>
  </RouterLink>
</template>
