<script setup lang="ts">
import { type AssetBalanceWithPrice, type BigNumber } from '@rotki/common';
import { Routes } from '@/router/routes';
import { SupportedExchange } from '@/types/exchanges';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';
import { type Nullable } from '@/types';

const props = withDefaults(
  defineProps<{
    exchange?: Nullable<SupportedExchange>;
  }>(),
  {
    exchange: null
  }
);

const { exchange } = toRefs(props);
const { isTaskRunning } = useTaskStore();
const { getBalances, refreshExchangeSavings } = useExchangeBalancesStore();
const { connectedExchanges } = storeToRefs(useHistoryStore());

const { refreshBalance } = useRefresh();

const refreshExchangeBalances = async () => {
  await Promise.all([refreshBalance('exchange'), refreshExchangeSavings(true)]);
};

const selectedExchange = ref<string>('');
const usedExchanges = computed<SupportedExchange[]>(() =>
  get(connectedExchanges)
    .map(({ location }) => location)
    .filter(uniqueStrings)
);

const isExchangeLoading = isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);

const router = useRouter();
const route = useRoute();

const setSelectedExchange = () => {
  set(selectedExchange, get(route).params.exchange);
};

onMounted(() => {
  setSelectedExchange();
});

watch(route, () => {
  setSelectedExchange();
});

const exchangeBalance = (exchange: SupportedExchange): BigNumber => {
  const balances = get(getBalances(exchange));
  return balances.reduce(
    (sum, asset: AssetBalanceWithPrice) => sum.plus(asset.usdValue),
    Zero
  );
};

const openExchangeDetails = async () => {
  await router.push({
    path: `${Routes.ACCOUNTS_BALANCES_EXCHANGE}/${get(selectedExchange)}`
  });
};

const balances = computed(() => {
  const currentExchange = get(exchange);
  if (!currentExchange) {
    return null;
  }
  return get(getBalances(currentExchange));
});

const exchangeDetailTabs: Ref<number> = ref(0);
watch(exchange, () => {
  set(exchangeDetailTabs, 0);
});

const { t, tc } = useI18n();

onMounted(() => {
  refreshExchangeSavings();
});

const isBinance = computed(() => {
  const exchangeVal = get(exchange);
  if (!exchangeVal) {
    return false;
  }
  return [SupportedExchange.BINANCE, SupportedExchange.BINANCEUS].includes(
    exchangeVal
  );
});
</script>

<template>
  <card class="exchange-balances mt-8" outlined-body>
    <template #title>
      <refresh-button
        class="exchange-balances__refresh"
        :loading="isExchangeLoading"
        :tooltip="tc('exchange_balances.refresh_tooltip')"
        @refresh="refreshExchangeBalances"
      />
      {{ tc('exchange_balances.title') }}
    </template>
    <v-btn
      v-blur
      fixed
      bottom
      right
      :fab="!$vuetify.breakpoint.xl"
      :rounded="$vuetify.breakpoint.xl"
      :x-large="$vuetify.breakpoint.xl"
      color="primary"
      to="/settings/api-keys/exchanges?add=true"
    >
      <v-icon> mdi-plus </v-icon>
      <div v-if="$vuetify.breakpoint.xl" class="ml-2">
        {{ tc('exchange_balances.add_exchange') }}
      </div>
    </v-btn>
    <v-row
      v-if="usedExchanges.length > 0"
      no-gutters
      class="exchange-balances__content"
    >
      <v-col cols="12" class="hidden-md-and-up">
        <v-select
          v-model="selectedExchange"
          filled
          :items="usedExchanges"
          hide-details
          :label="tc('exchange_balances.select_exchange')"
          class="exchange-balances__content__select"
          @change="openExchangeDetails"
        >
          <template #selection="{ item }">
            <exchange-amount-row
              :balance="exchangeBalance(item)"
              :exchange="item"
            />
          </template>
          <template #item="{ item }">
            <exchange-amount-row
              :balance="exchangeBalance(item)"
              :exchange="item"
            />
          </template>
        </v-select>
      </v-col>
      <v-col cols="2" class="hidden-sm-and-down">
        <v-tabs
          fixed-tabs
          vertical
          hide-slider
          optional
          class="exchange-balances__tabs"
        >
          <v-tab
            v-for="(usedExchange, i) in usedExchanges"
            :key="i"
            class="exchange-balances__tab text-none"
            active-class="exchange-balances__tab--active"
            :to="`/accounts-balances/exchange-balances/${usedExchange}`"
            @click="selectedExchange = usedExchange"
          >
            <location-display :identifier="usedExchange" size="36px" />
            <div class="exchange-balances__tab__amount d-block">
              <amount-display
                show-currency="symbol"
                fiat-currency="USD"
                :value="exchangeBalance(usedExchange)"
              />
            </div>
          </v-tab>
        </v-tabs>
      </v-col>
      <v-col
        :class="
          $vuetify.breakpoint.mdAndUp ? 'exchange-balances__balances' : null
        "
      >
        <div>
          <div v-if="exchange">
            <v-tabs v-model="exchangeDetailTabs">
              <v-tab>{{ t('exchange_balances.tabs.balances') }}</v-tab>
              <v-tab v-if="isBinance">{{
                t('exchange_balances.tabs.savings_interest_history')
              }}</v-tab>
            </v-tabs>

            <v-divider />

            <v-tabs-items v-model="exchangeDetailTabs">
              <v-tab-item class="pa-4">
                <v-sheet outlined rounded>
                  <asset-balances
                    hide-breakdown
                    :loading="isExchangeLoading"
                    :balances="balances"
                  />
                </v-sheet>
              </v-tab-item>
              <v-tab-item v-if="isBinance" class="pa-4">
                <binance-saving-detail :exchange="exchange" />
              </v-tab-item>
            </v-tabs-items>
          </div>

          <div v-else class="pa-4">
            {{ t('exchange_balances.select_hint') }}
          </div>
        </div>
      </v-col>
    </v-row>
    <v-row v-else class="px-4 py-8">
      <v-col>
        <i18n path="exchange_balances.no_connected_exchanges">
          <router-link to="/settings/api-keys/exchanges">
            {{ t('exchange_balances.click_here') }}
          </router-link>
        </i18n>
      </v-col>
    </v-row>
  </card>
</template>

<style scoped lang="scss">
.exchange-balances {
  &__balances {
    border-left: var(--v-rotki-light-grey-darken1) solid thin;
  }

  &__tabs {
    border-radius: 4px 0 0 4px;
    height: 100%;

    /* stylelint-disable selector-class-pattern,selector-nested-pattern */

    :deep(.v-tabs-bar__content) {
      /* stylelint-enable selector-class-pattern,selector-nested-pattern */
      background-color: var(--v-rotki-light-grey-darken1);
      border-radius: 4px 0 0 4px;
      height: 100%;
    }
  }

  &__tab {
    display: flex;
    flex-direction: column;
    min-height: 125px !important;
    max-height: 125px !important;
    padding-top: 15px;
    padding-bottom: 15px;
    filter: grayscale(100%);
    color: var(--v-rotki-grey-base);
    background-color: transparent;

    &:hover {
      filter: grayscale(0);
      background-color: var(--v-rotki-light-grey-base);
      border-radius: 4px 0 0 4px;
    }

    &:focus {
      filter: grayscale(0);
      border-radius: 4px 0 0 4px;
    }

    &--active {
      filter: grayscale(0);
      border-radius: 4px 0 0 4px;
      background-color: white;
      color: var(--v-secondary-base);

      &:hover {
        border-radius: 4px 0 0 4px;
        background-color: white;
        opacity: 1 !important;
      }

      &:focus {
        border-radius: 4px 0 0 4px;
        opacity: 1 !important;
      }
    }

    /* stylelint-disable selector-class-pattern,selector-nested-pattern */

    .theme--dark &--active {
      background-color: var(--v-dark-lighten1);
      color: white;

      &:hover {
        background-color: var(--v-dark-base) !important;
      }
    }
    /* stylelint-enable selector-class-pattern,selector-nested-pattern */
  }
}
</style>
