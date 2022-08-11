<template>
  <card full-height>
    <template #title>{{ $t('kraken_staking_overview.title') }}</template>
    <v-row class="pt-1 pb-4">
      <v-col>
        <v-row no-gutters>
          <v-col>
            <div class="font-weight-medium">
              {{ $t('kraken_staking_overview.earned') }}
            </div>
          </v-col>
        </v-row>
        <v-row justify="space-between" align="center" no-gutters class="mt-2">
          <v-col cols="auto">
            <div
              class="d-flex align-center text--secondary font-weight-light ms-2"
            >
              {{ $t('kraken_staking_overview.historical') }}
              <v-tooltip open-delay="400" top>
                <template #activator="{ attrs, on }">
                  <v-icon class="ms-1" small v-bind="attrs" v-on="on">
                    mdi-information
                  </v-icon>
                </template>
                <span>{{ $t('kraken_staking_overview.hint.historical') }}</span>
              </v-tooltip>
            </div>
          </v-col>
          <v-col cols="auto">
            <div class="d-flex align-center">
              <value-accuracy-hint />
              <amount-display
                show-currency="ticker"
                fiat-currency="USD"
                :value="totalUsd"
                class="grey--text"
              />
            </div>
          </v-col>
        </v-row>
        <v-row justify="space-between" align="center" no-gutters class="mt-2">
          <v-col cols="auto">
            <div
              class="d-flex align-center text--secondary font-weight-light ms-2"
            >
              {{ $t('kraken_staking_overview.current') }}
              <v-tooltip open-delay="400" top>
                <template #activator="{ attrs, on }">
                  <v-icon class="ms-1" small v-bind="attrs" v-on="on">
                    mdi-information
                  </v-icon>
                </template>
                <span>{{ $t('kraken_staking_overview.hint.current') }}</span>
              </v-tooltip>
            </div>
          </v-col>
          <v-col cols="auto">
            <amount-display
              show-currency="ticker"
              fiat-currency="USD"
              :loading="pricesAreLoading"
              :value="totalUsdCurrent"
              class="grey--text"
            />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </card>
</template>
<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import ValueAccuracyHint from '@/components/helper/hint/ValueAccuracyHint.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { ReceivedAmount } from '@/types/staking';
import { assert } from '@/utils/assertions';
import { Zero } from '@/utils/bignumbers';

export default defineComponent({
  name: 'KrakenStakingOverview',
  components: { ValueAccuracyHint },
  props: {
    totalUsd: { required: true, type: BigNumber },
    earned: { required: true, type: Array as PropType<ReceivedAmount[]> }
  },
  setup(props) {
    const { earned } = toRefs(props);
    const { prices } = storeToRefs(useBalancePricesStore());
    const pricesAreLoading = computed(() => {
      const assetPrices = get(prices);
      return Object.keys(assetPrices).length === 0;
    });
    const totalUsdCurrent = computed<BigNumber>(() => {
      const earnedAssets = get(earned);
      const assetPrices = get(prices);
      if (Object.keys(assetPrices).length === 0) {
        return Zero;
      }

      let sum = Zero;

      for (const { asset, amount } of earnedAssets) {
        const assetPrice = assetPrices[asset];
        assert(assetPrice);
        sum = sum.plus(assetPrice.times(amount));
      }
      return sum;
    });

    return {
      totalUsdCurrent,
      pricesAreLoading
    };
  }
});
</script>
