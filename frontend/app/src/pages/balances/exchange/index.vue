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
const { getBalances, refreshExchangeSavings, fetchExchangeSavings } =
  useExchangeBalancesStore();
const { connectedExchanges } = storeToRefs(useExchangesStore());

const { refreshBalance } = useRefresh();

const refreshExchangeBalances = async () => {
  await Promise.all([refreshBalance('exchange'), refreshExchangeSavings(true)]);
  await checkSavingsData();
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

const exchangeSavingsExist: Ref<boolean> = ref(false);

const exchangeDetailTabs: Ref<number> = ref(0);

watch(exchange, () => {
  set(exchangeDetailTabs, 0);
  checkSavingsData();
});

const checkSavingsData = async () => {
  const exchangeVal = get(exchange);
  if (exchangeVal && get(isBinance)) {
    const { total } = await fetchExchangeSavings({
      limit: 1,
      offset: 0,
      location: exchangeVal
    });

    set(exchangeSavingsExist, !!total);
  } else {
    set(exchangeSavingsExist, false);
  }
};

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
  <TablePageLayout
    :title="[
      t('navigation_menu.accounts_balances'),
      t('exchange_balances.title')
    ]"
  >
    <template #buttons>
      <RuiTooltip open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            class="exchange-balances__refresh"
            :disabled="exchangeDetailTabs !== 0"
            :loading="isExchangeLoading"
            @click="refreshExchangeBalances()"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('exchange_balances.refresh_tooltip') }}
      </RuiTooltip>
      <RuiButton v-blur color="primary" @click="navigate()">
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('exchange_balances.add_exchange') }}
      </RuiButton>
    </template>
    <RuiCard class="exchange-balances">
      <div v-if="usedExchanges.length > 0" class="flex flex-col md:flex-row">
        <div class="md:hidden mb-2">
          <VSelect
            v-model="selectedExchange"
            outlined
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
        </div>
        <div class="hidden md:block w-1/6 border-r border-default">
          <RuiTabs vertical color="primary" :value="usedExchanges">
            <template #default>
              <RuiTab
                v-for="(usedExchange, i) in usedExchanges"
                :key="i"
                link
                class="h-[8rem]"
                :to="`/accounts-balances/exchange-balances/${usedExchange}`"
                :value="usedExchange"
              >
                <LocationDisplay
                  :open-details="false"
                  :identifier="usedExchange"
                  size="36px"
                />
                <AmountDisplay
                  class="mt-1 text-xl"
                  show-currency="symbol"
                  fiat-currency="USD"
                  :value="exchangeBalance(usedExchange)"
                />
              </RuiTab>
            </template>
          </RuiTabs>
        </div>
        <div class="flex-1">
          <div v-if="exchange">
            <RuiTabs v-model="exchangeDetailTabs" color="primary">
              <template #default>
                <RuiTab>{{ t('exchange_balances.tabs.balances') }}</RuiTab>
                <RuiTab v-if="isBinance && exchangeSavingsExist">
                  {{ t('exchange_balances.tabs.savings_interest_history') }}
                </RuiTab>
              </template>
            </RuiTabs>

            <RuiDivider />

            <RuiTabItems v-model="exchangeDetailTabs">
              <template #default>
                <RuiTabItem class="pt-4 md:pl-4">
                  <AssetBalances
                    hide-breakdown
                    :loading="isExchangeLoading"
                    :balances="balances"
                  />
                </RuiTabItem>
                <RuiTabItem
                  v-if="isBinance && exchangeSavingsExist"
                  class="md:pl-4"
                >
                  <BinanceSavingDetail :exchange="exchange" />
                </RuiTabItem>
              </template>
            </RuiTabItems>
          </div>

          <div v-else class="p-4">
            {{ t('exchange_balances.select_hint') }}
          </div>
        </div>
      </div>
      <div v-else class="px-4 py-8">
        <i18n path="exchange_balances.no_connected_exchanges">
          <InternalLink
            :to="Routes.API_KEYS_EXCHANGES"
            class="module-not-active__link font-weight-regular text-body-1 text-decoration-none"
          >
            {{ t('exchange_balances.click_here') }}
          </InternalLink>
        </i18n>
      </div>
    </RuiCard>
  </TablePageLayout>
</template>
