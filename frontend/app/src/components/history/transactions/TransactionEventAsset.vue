<script setup lang="ts">
import { type AssetBalance } from '@rotki/common';
import { type ComputedRef, type PropType } from 'vue';
import TransactionEventExtraData from '@/components/history/transactions/TransactionEventExtraData.vue';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { TransactionEventType } from '@/types/transaction';
import { getEventType } from '@/utils/history';
import { type EthTransactionEventEntry } from '@/types/history/tx';

const props = defineProps({
  event: {
    required: true,
    type: Object as PropType<EthTransactionEventEntry>
  }
});

const { event } = toRefs(props);
const { assetSymbol } = useAssetInfoRetrieval();

const showBalance = computed<boolean>(() => {
  return getEventType(get(event)) !== TransactionEventType.APPROVAL;
});

const eventAsset = computed(() => get(event).asset);
const symbol = assetSymbol(eventAsset);

const staking: ComputedRef<AssetBalance | null> = computed(() => {
  const stakingProtocols = ['liquity'];
  const { counterparty: protocol, extraData, balance, asset } = get(event);

  if (!(protocol && stakingProtocols.includes(protocol))) {
    return null;
  }

  const stakedAmount = extraData?.stakedAmount;
  if (!stakedAmount) {
    return null;
  }
  const { usdValue, amount } = balance;
  const usdPrice = usdValue.div(amount);

  return {
    asset,
    usdValue: stakedAmount.multipliedBy(usdPrice),
    amount: stakedAmount
  };
});
</script>
<template>
  <div>
    <div class="py-2 d-flex align-center">
      <div class="mr-2">
        <asset-link :asset="event.asset" icon>
          <asset-icon size="32px" :identifier="event.asset" />
        </asset-link>
      </div>
      <div v-if="showBalance">
        <div>
          <amount-display :value="event.balance.amount" :asset="event.asset" />
        </div>
        <div>
          <amount-display
            :value="event.balance.usdValue"
            fiat-currency="USD"
            class="grey--text"
          />
        </div>
      </div>
      <div v-else>
        {{ symbol }}
      </div>
    </div>
    <transaction-event-extra-data v-if="staking" :staking="staking" />
  </div>
</template>
