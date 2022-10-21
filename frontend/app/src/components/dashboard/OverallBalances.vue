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
            class="pa-1 px-2 overall-balances__net-worth-change__pill"
          >
            <loading
              v-if="isLoading"
              class="overall-balances__net-worth__loading d-flex justify-center mt-n2"
            />
            <span v-else class="d-flex flex-row">
              <span class="me-2">
                <v-icon>{{ indicator }}</v-icon>
              </span>
              <amount-display
                v-if="!isLoading"
                show-currency="symbol"
                :fiat-currency="currencySymbol"
                :value="balanceDelta"
              />
              <percentage-display
                v-if="!isLoading"
                class="ms-2 px-1 text--secondary pe-2"
                :value="percentage"
              />
            </span>
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
            v-if="!isLoading"
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
              {{ t('overall_balances.loading') }}
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
import dayjs from 'dayjs';
import NetWorthChart from '@/components/dashboard/NetWorthChart.vue';
import Loading from '@/components/helper/Loading.vue';
import TimeframeSelector from '@/components/helper/TimeframeSelector.vue';
import { useSectionLoading } from '@/composables/common';
import { usePremiumStore } from '@/store/session/premium';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { isPeriodAllowed } from '@/store/settings/utils';
import { useStatisticsStore } from '@/store/statistics';
import { Section } from '@/types/status';
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';

const { t } = useI18n();
const { currencySymbol, floatingPrecision } = storeToRefs(
  useGeneralSettingsStore()
);
const sessionStore = useSessionSettingsStore();
const { update } = sessionStore;
const { timeframe } = storeToRefs(sessionStore);
const { premium } = storeToRefs(usePremiumStore());
const statistics = useStatisticsStore();
const { fetchNetValue, getNetValue } = statistics;
const { totalNetWorth } = storeToRefs(statistics);
const frontendStore = useFrontendSettingsStore();
const { visibleTimeframes } = storeToRefs(frontendStore);

const { isSectionRefreshing } = useSectionLoading();
const isLoading = computed(() => {
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
  if (get(isLoading)) {
    return '';
  }
  return get(balanceDelta).isNegative() ? 'mdi-menu-down' : 'mdi-menu-up';
});

const balanceClass = computed(() => {
  if (get(isLoading)) {
    return 'rotki-grey lighten-3';
  }
  return get(balanceDelta).isNegative() ? 'rotki-red lighten-1' : 'rotki-green';
});

const setTimeframe = async (value: TimeFrameSetting) => {
  assert(value !== TimeFramePersist.REMEMBER);
  sessionStore.update({ timeframe: value });
  await frontendStore.updateSetting({ lastKnownTimeframe: value });
};

watch(premium, async () => fetchNetValue());

onMounted(() => {
  const isPremium = get(premium);
  const selectedTimeframe = get(timeframe);
  if (!isPremium && !isPeriodAllowed(selectedTimeframe)) {
    update({ timeframe: TimeFramePeriod.TWO_WEEKS });
  }
});

const { showGraphRangeSelector } = storeToRefs(useFrontendSettingsStore());
const chartSectionHeight = computed<string>(() => {
  const height = 208 + (get(showGraphRangeSelector) ? 60 : 0);
  return `${height}px`;
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
    :deep() {
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
      min-height: v-bind(chartSectionHeight);
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
