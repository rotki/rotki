<template>
  <div
    v-if="
      isStakingProtocol &&
      event.extraData &&
      event.extraData.asset &&
      stakedUsdValue
    "
    :class="css['total-staked-indicator']"
    class="pl-6"
  >
    <div class="grey--text d-flex align-center py-2">
      {{ tc('transactions.events.extra.total_staked_by_this_tx') }}:
    </div>
    <div class="py-2 d-flex align-center">
      <div class="mr-2">
        <asset-link :asset="event.extraData.asset" icon>
          <asset-icon size="32px" :identifier="event.extraData.asset" />
        </asset-link>
      </div>
      <div>
        <div>
          <amount-display
            :value="event.extraData.stakedAmount"
            :asset="event.extraData.asset"
          />
        </div>
        <div>
          <amount-display
            :value="stakedUsdValue"
            fiat-currency="USD"
            class="grey--text"
          />
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { ComputedRef, PropType } from 'vue';
import { EthTransactionEventEntry } from '@/store/history/types';

const props = defineProps({
  event: {
    required: true,
    type: Object as PropType<EthTransactionEventEntry>
  }
});

const { event } = toRefs(props);

const stakingProtocols = ['liquity'];
const isStakingProtocol: ComputedRef<boolean> = computed(() => {
  const protocol = get(event).counterparty;
  return !!(protocol && stakingProtocols.includes(protocol));
});

const stakedUsdValue: ComputedRef<BigNumber | null> = computed(() => {
  const stakedAmount = get(event)?.extraData?.stakedAmount;
  if (!get(isStakingProtocol) || !stakedAmount) {
    return null;
  }

  const { usdValue, amount } = get(event).balance;
  const usdPrice = usdValue.div(amount);

  return stakedAmount.multipliedBy(usdPrice);
});

const css = useCssModule();
const { tc } = useI18n();
</script>

<style lang="scss" module>
.total-staked-indicator {
  border-left: 3px solid var(--v-success-base);
}
</style>
