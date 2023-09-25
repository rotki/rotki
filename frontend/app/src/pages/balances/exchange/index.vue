<script setup lang="ts">
import { type AssetBalanceWithPrice, type BigNumber } from '@rotki/common';
import { Routes } from '@/router/routes';
import { SupportedExchange } from '@/types/exchanges';
import { TaskType } from '@/types/task-type';
import { type Nullable } from '@/types';

const props = withDefaults(
  defineProps<{
    exchange?: Nullable<SupportedExchange>;
  }>(),
  {
    exchange: null
  }
);

const { t } = useI18n();

const { exchange } = toRefs(props);
const { isTaskRunning } = useTaskStore();
const { getBalances, refreshExchangeSavings } = useExchangeBalancesStore();
const { connectedExchanges } = storeToRefs(useExchangesStore());

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

const vueRouter = useRouter();
const navigate = () => {
  vueRouter.push('/settings/api-keys/exchanges?add=true');
};

const exchangeDetailTabs: Ref<number> = ref(0);
watch(exchange, () => {
  set(exchangeDetailTabs, 0);
});

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

const { mdAndUp } = useDisplay();
</script>

<template>
  <TablePageLayout>
    <template #buttons>
      <RuiButton v-blur color="primary" @click="navigate()">
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('exchange_balances.add_exchange') }}
      </RuiButton>
    </template>
    <RuiCard class="exchange-balances">
      <template #header>
        <div class="flex flex-row items-center gap-2">
          <RefreshButton
            class="exchange-balances__refresh"
            :loading="isExchangeLoading"
            :tooltip="t('exchange_balances.refresh_tooltip')"
            @refresh="refreshExchangeBalances()"
          />
          <CardTitle>{{ t('exchange_balances.title') }}</CardTitle>
        </div>
      </template>
      <VSheet outlined class="rounded-xl overflow-hidden">
        <VRow
          v-if="usedExchanges.length > 0"
          no-gutters
          class="exchange-balances__content"
        >
          <VCol cols="12" class="hidden-md-and-up">
            <VSelect
              v-model="selectedExchange"
              filled
              :items="usedExchanges"
              hide-details
              :label="t('exchange_balances.select_exchange')"
              class="exchange-balances__content__select"
              @change="openExchangeDetails()"
            >
              <template #selection="{ item }">
                <ExchangeAmountRow
                  :balance="exchangeBalance(item)"
                  :exchange="item"
                />
              </template>
              <template #item="{ item }">
                <ExchangeAmountRow
                  :balance="exchangeBalance(item)"
                  :exchange="item"
                />
              </template>
            </VSelect>
          </VCol>
          <VCol cols="2" class="hidden-sm-and-down">
            <VTabs
              fixed-tabs
              vertical
              hide-slider
              optional
              class="exchange-balances__tabs"
            >
              <VTab
                v-for="(usedExchange, i) in usedExchanges"
                :key="i"
                class="exchange-balances__tab text-none"
                active-class="exchange-balances__tab--active"
                :to="`/accounts-balances/exchange-balances/${usedExchange}`"
                @click="selectedExchange = usedExchange"
              >
                <LocationDisplay :identifier="usedExchange" size="36px" />
                <div class="exchange-balances__tab__amount d-block">
                  <AmountDisplay
                    show-currency="symbol"
                    fiat-currency="USD"
                    :value="exchangeBalance(usedExchange)"
                  />
                </div>
              </VTab>
            </VTabs>
          </VCol>
          <VCol :class="mdAndUp ? 'exchange-balances__balances' : null">
            <div>
              <div v-if="exchange">
                <VTabs v-model="exchangeDetailTabs">
                  <VTab>{{ t('exchange_balances.tabs.balances') }}</VTab>
                  <VTab v-if="isBinance">{{
                    t('exchange_balances.tabs.savings_interest_history')
                  }}</VTab>
                </VTabs>

                <VDivider />

                <VTabsItems v-model="exchangeDetailTabs">
                  <VTabItem class="pa-4">
                    <AssetBalances
                      hide-breakdown
                      :loading="isExchangeLoading"
                      :balances="balances"
                    />
                  </VTabItem>
                  <VTabItem v-if="isBinance" class="pa-4">
                    <BinanceSavingDetail :exchange="exchange" />
                  </VTabItem>
                </VTabsItems>
              </div>

              <div v-else class="pa-4">
                {{ t('exchange_balances.select_hint') }}
              </div>
            </div>
          </VCol>
        </VRow>
        <VRow v-else class="px-4 py-8">
          <VCol>
            <i18n path="exchange_balances.no_connected_exchanges">
              <InternalLink
                :to="Routes.API_KEYS_EXCHANGES"
                class="module-not-active__link font-weight-regular text-body-1 text-decoration-none"
              >
                {{ t('exchange_balances.click_here') }}
              </InternalLink>
            </i18n>
          </VCol>
        </VRow>
      </VSheet>
    </RuiCard>
  </TablePageLayout>
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
