<template>
  <card class="exchange-balances mt-8" outlined-body>
    <template #title>
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
        <asset-balances
          v-if="exchange"
          :loading="isExchangeLoading"
          :balances="balances"
        />
        <div v-else class="pa-4">
          {{ t('exchange_balances.select_hint') }}
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

<script setup lang="ts">
import { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { PropType } from 'vue';
import ExchangeAmountRow from '@/components/accounts/exchanges/ExchangeAmountRow.vue';
import AssetBalances from '@/components/AssetBalances.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Routes } from '@/router/routes';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useTasks } from '@/store/tasks';
import { SupportedExchange } from '@/types/exchanges';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';

const props = defineProps({
  exchange: {
    required: false,
    type: String as PropType<SupportedExchange>,
    default: ''
  }
});

const { exchange } = toRefs(props);
const { isTaskRunning } = useTasks();
const store = useExchangeBalancesStore();
const { connectedExchanges } = storeToRefs(store);

const selectedExchange = ref<string>('');
const usedExchanges = computed<SupportedExchange[]>(() => {
  return get(connectedExchanges)
    .map(({ location }) => location)
    .filter(uniqueStrings);
});

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
  const balances = get(store.getBalances(exchange));
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
  let currentExchange = get(exchange);
  return get(store.getBalances(currentExchange));
});

const { t, tc } = useI18n();
</script>

<style scoped lang="scss">
:deep() {
  .v-tabs-bar {
    &__content {
      background-color: var(--v-rotki-light-grey-darken1);
      border-radius: 4px 0 0 4px;
      height: 100%;
    }
  }

  .v-tab {
    &__active {
      &::before {
        opacity: 1 !important;
      }
    }
  }
}

.exchange-balances {
  &__balances {
    border-left: var(--v-rotki-light-grey-darken1) solid thin;
  }

  &__tabs {
    border-radius: 4px 0 0 4px;
    height: 100%;
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

    /* stylelint-disable selector-class-pattern,selector-nested-pattern, rule-empty-line-before */
    .theme--dark &--active {
      background-color: var(--v-dark-lighten1);
      color: white;

      &:hover {
        background-color: var(--v-dark-base) !important;
      }
    }
    /* stylelint-enable selector-class-pattern,selector-nested-pattern, rule-empty-line-before */
  }
}
</style>
