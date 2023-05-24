<script setup lang="ts">
import { type AssetBalance } from '@rotki/common';
import {
  type HistoryEventDetail,
  type HistoryEventEntry
} from '@/types/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const { event } = toRefs(props);

const { getEventDetails } = useHistoryEventsApi();

const loading: Ref<boolean> = ref(false);
const extraData: Ref<HistoryEventDetail | null> = ref(null);

onBeforeMount(async () => {
  const { identifier } = get(event);
  if (identifier) {
    set(loading, true);
    set(extraData, await getEventDetails(identifier));
    set(loading, false);
  }
});

const stakingDetail: ComputedRef<AssetBalance | null> = computed(() => {
  const { balance, identifier } = get(event);
  if (!identifier) {
    return null;
  }

  const data = get(extraData)?.liquityStaking;
  if (!data) {
    return null;
  }

  const stakedAmount = data.stakedAmount;
  const { usdValue, amount } = balance;
  const usdPrice = usdValue.div(amount);

  return {
    asset: data.asset,
    usdValue: stakedAmount.multipliedBy(usdPrice),
    amount: stakedAmount
  };
});

const css = useCssModule();
const { t } = useI18n();
</script>

<template>
  <div
    v-if="stakingDetail || loading"
    :class="css['total-staked-indicator']"
    class="pl-6"
  >
    <template v-if="loading">
      <v-skeleton-loader width="100" type="text" />
    </template>
    <template v-else-if="stakingDetail">
      <div class="grey--text d-flex align-center py-2">
        {{ t('transactions.events.extra.total_staked_by_this_tx') }}:
      </div>
      <div class="py-2 d-flex align-center">
        <div class="mr-2">
          <asset-link :asset="stakingDetail.asset" icon>
            <asset-icon size="32px" :identifier="stakingDetail.asset" />
          </asset-link>
        </div>
        <div>
          <div>
            <amount-display
              :value="stakingDetail.amount"
              :asset="stakingDetail.asset"
            />
          </div>
          <div>
            <amount-display
              :value="stakingDetail.usdValue"
              fiat-currency="USD"
              class="grey--text"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" module>
.total-staked-indicator {
  border-left: 3px solid var(--v-success-base);
}
</style>
