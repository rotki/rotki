<template>
  <v-card class="overall-balances">
    <v-row no-gutters class="pa-5">
      <v-col
        cols="12"
        md="6"
        lg="5"
        class="d-flex flex-column align-center justify-center"
      >
        <div
          class="overall-balances__net-worth text-center font-weight-medium mb-2"
        >
          <loading
            v-if="loading"
            class="overall-balances__net-worth__loading text-start ms-2"
          />
          <div :style="`font-size: ${adjustedTotalNetWorthFontSize}em`">
            <amount-display
              class="ps-4"
              show-currency="symbol"
              :fiat-currency="currencySymbol"
              :value="totalNetWorth"
            />
          </div>
        </div>
        <div class="overall-balances__net-worth-change py-2">
          <span
            :class="balanceClass"
            class="pa-1 px-2 d-flex flex-row overall-balances__net-worth-change__pill"
          >
            <span class="me-2">{{ indicator }}</span>
            <amount-display
              v-if="!loading"
              show-currency="symbol"
              :fiat-currency="currencySymbol"
              :value="balanceDelta"
            />
            <percentage-display
              v-if="!loading"
              class="ms-2 px-1 text--secondary pe-2"
              :value="percentage"
            />
          </span>
        </div>
        <timeframe-selector
          :value="timeframe"
          :visible-timeframes="visibleTimeframes"
          @input="setTimeframe"
        />
      </v-col>
      <v-col cols="12" md="6" lg="7" class="d-flex">
        <div
          class="d-flex justify-center align-center flex-grow-1 overall-balances__net-worth-chart"
        >
          <net-worth-chart
            v-if="!loading"
            :chart-data="timeframeData"
            :timeframe="timeframe"
            :timeframes="allTimeframes"
          />
          <div v-else class="overall-balances__net-worth-chart__loader">
            <v-progress-circular
              indeterminate
              class="align-self-center"
              color="primary"
            />
            <div class="pt-5 text-caption">
              {{ $t('overall_balances.loading') }}
            </div>
          </div>
        </div>
      </v-col>
    </v-row>
  </v-card>
</template>

<script setup lang="ts">
import { TimeUnit } from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  TimeFramePersist,
  timeframes,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { get, set } from '@vueuse/core';
import dayjs from 'dayjs';
import { storeToRefs } from 'pinia';
import { computed, onMounted, watch } from 'vue';
import NetWorthChart from '@/components/dashboard/NetWorthChart.vue';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import Loading from '@/components/helper/Loading.vue';
import TimeframeSelector from '@/components/helper/TimeframeSelector.vue';
import { setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { usePremiumStore } from '@/store/session/premium';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { isPeriodAllowed } from '@/store/settings/utils';
import { useStatisticsStore } from '@/store/statistics';
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';

const { currencySymbol, floatingPrecision } = storeToRefs(
  useGeneralSettingsStore()
);
const { timeframe } = storeToRefs(useSessionSettingsStore());
const { premium } = storeToRefs(usePremiumStore());
const statistics = useStatisticsStore();
const { fetchNetValue, getNetValue } = statistics;
const { totalNetWorth } = storeToRefs(statistics);
const frontendStore = useFrontendSettingsStore();
const { visibleTimeframes } = storeToRefs(frontendStore);

const { isSectionRefreshing } = setupStatusChecking();
const loading = computed(() => {
  return (
    get(isSectionRefreshing(Section.BLOCKCHAIN_ETH)) ||
    get(isSectionRefreshing(Section.BLOCKCHAIN_BTC))
  );
});

const startingValue = computed(() => {
  const data = get(timeframeData).data;
  let start = data[0];
  if (start === 0) {
    for (let i = 1; i < data.length; i++) {
      if (data[i] > 0) {
        start = data[i];
        break;
      }
    }
  }
  return bigNumberify(start);
});

const adjustedTotalNetWorthFontSize = computed(() => {
  const digits = get(totalNetWorth)
    .toFormat(get(floatingPrecision))
    .replace(/\./g, '')
    .replace(/,/g, '').length;

  // this number adjusted visually
  // when we use max floating precision (8), it won't overlap
  return Math.min(1, 12 / digits);
});

const allTimeframes = computed(() => {
  return timeframes((unit, amount) =>
    dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()
  );
});

const balanceDelta = computed(() => {
  return get(totalNetWorth).minus(get(startingValue));
});

const timeframeData = computed(() => {
  const all = get(allTimeframes);
  let selection = get(timeframe);
  const startingDate = all[selection].startingDate();
  return get(getNetValue(startingDate));
});

const percentage = computed(() => {
  const bigNumber = get(balanceDelta).div(get(startingValue)).multipliedBy(100);

  return bigNumber.isFinite() ? bigNumber.toFormat(2) : '-';
});

const indicator = computed(() => {
  if (get(loading)) {
    return '';
  }
  return get(balanceDelta).isNegative() ? '▼' : '▲';
});

const balanceClass = computed(() => {
  if (get(loading)) {
    return 'rotki-grey lighten-3';
  }
  return get(balanceDelta).isNegative() ? 'rotki-red lighten-1' : 'rotki-green';
});

const setTimeframe = (value: TimeFrameSetting) => {
  assert(value !== TimeFramePersist.REMEMBER);
  set(timeframe, value);
  frontendStore.updateSetting({ lastKnownTimeframe: value });
};

watch(premium, async () => fetchNetValue());

onMounted(() => {
  const isPremium = get(premium);
  const selectedTimeframe = get(timeframe);
  if (isPremium && !isPeriodAllowed(selectedTimeframe)) {
    set(timeframe, TimeFramePeriod.TWO_WEEKS);
  }
});
</script>
<style scoped lang="scss">
.overall-balances {
  &__balance {
    display: flex;
    justify-content: center;
    align-items: baseline;
  }

  &__net-worth {
    ::v-deep {
      .amount-display {
        &__value {
          font-size: 3.5em;
          line-height: 4rem;
          @media (max-width: 450px) {
            font-size: 2.4em;
            line-height: 2.4rem;
          }
        }

        .amount-currency {
          font-size: 2rem;
        }
      }
    }

    &__loading {
      font-size: 1.5em;
      line-height: 1em;
      margin-bottom: -10px;
    }
  }

  &__net-worth-change {
    display: flex;
    justify-content: center;
    align-items: baseline;
    margin-bottom: 1em;
    min-height: 32px;

    span {
      border-radius: 0.75em;
    }

    &__pill {
      min-height: 32px;
      min-width: 170px;
    }
  }

  &__net-worth-chart {
    width: 100%;

    &__loader {
      display: flex;
      height: 100%;
      flex-direction: column;
      align-content: center;
      justify-content: center;
      text-align: center;
    }
  }
}
</style>
