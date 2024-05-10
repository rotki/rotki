<script setup lang="ts">
import { Routes } from '@/router/routes';
import { TaskType } from '@/types/task-type';
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { Nullable } from '@/types';

const props = withDefaults(
  defineProps<{
    exchange?: Nullable<string>;
  }>(),
  {
    exchange: null,
  },
);

const { t } = useI18n();
const selectedTab = ref<string | undefined>(props.exchange ?? undefined);

const { exchange } = toRefs(props);
const { isTaskRunning } = useTaskStore();
const { getBalances, refreshExchangeSavings, fetchExchangeSavings }
  = useExchangeBalancesStore();
const { connectedExchanges } = storeToRefs(useExchangesStore());

const { refreshBalance } = useRefresh();

async function refreshExchangeBalances() {
  await Promise.all([refreshBalance('exchange'), refreshExchangeSavings(true)]);
  await checkSavingsData();
}

const selectedExchange = ref<string>('');
const usedExchanges = computed<string[]>(() =>
  get(connectedExchanges)
    .map(({ location }) => location)
    .filter(uniqueStrings),
);

const isExchangeLoading = isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);

const router = useRouter();
const route = useRoute();

function setSelectedExchange() {
  set(selectedExchange, get(route).params.exchange);
}

onMounted(() => {
  setSelectedExchange();
});

watch(route, () => {
  setSelectedExchange();
});

function exchangeBalance(exchange: string): BigNumber {
  const balances = get(getBalances(exchange));
  return balances.reduce(
    (sum, asset: AssetBalanceWithPrice) => sum.plus(asset.usdValue),
    Zero,
  );
}

async function openExchangeDetails() {
  await router.push({
    path: `${Routes.ACCOUNTS_BALANCES_EXCHANGE}/${get(selectedExchange)}`,
  });
}

const balances = computed(() => {
  const currentExchange = get(exchange);
  if (!currentExchange)
    return [];

  return get(getBalances(currentExchange));
});

const vueRouter = useRouter();

function navigate() {
  vueRouter.push({
    path: Routes.API_KEYS_EXCHANGES,
    query: { add: 'true' },
  });
}

const exchangeSavingsExist: Ref<boolean> = ref(false);
const exchangeDetailTabs: Ref<number> = ref(0);

watch(exchange, () => {
  set(exchangeDetailTabs, 0);
  checkSavingsData();
});

async function checkSavingsData() {
  const exchangeVal = get(exchange);
  if (isBinance(exchangeVal)) {
    const { total } = await fetchExchangeSavings({
      limit: 1,
      offset: 0,
      location: exchangeVal,
    });

    set(exchangeSavingsExist, !!total);
  }
  else {
    set(exchangeSavingsExist, false);
  }
}

onMounted(() => {
  refreshExchangeSavings();
});

function isBinance(exchange: string | null): exchange is 'binance' | 'binanceus' {
  return !!exchange && ['binance', 'binanceus'].includes(exchange);
}
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.accounts_balances'),
      t('exchange_balances.title'),
    ]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
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
      <RuiButton
        v-blur
        color="primary"
        @click="navigate()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('exchange_balances.add_exchange') }}
      </RuiButton>
    </template>
    <RuiCard class="exchange-balances">
      <div
        v-if="usedExchanges.length > 0"
        class="flex flex-col md:flex-row"
      >
        <div class="md:hidden mb-4">
          <RuiMenuSelect
            v-model="selectedExchange"
            :options="usedExchanges"
            :label="t('exchange_balances.select_exchange')"
            key-attr="key"
            full-width
            variant="outlined"
            @input="openExchangeDetails()"
          >
            <template #activator.text="{ value }">
              <ExchangeAmountRow
                class="pr-3"
                :balance="exchangeBalance(value.key)"
                :exchange="value.key"
              />
            </template>
            <template #item.text="{ option }">
              <ExchangeAmountRow
                :balance="exchangeBalance(option.key)"
                :exchange="option.key"
              />
            </template>
          </RuiMenuSelect>
        </div>
        <div class="hidden md:block w-1/6 border-r border-default">
          <RuiTabs
            v-model="selectedTab"
            vertical
            color="primary"
          >
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
            <RuiTabs
              v-model="exchangeDetailTabs"
              color="primary"
            >
              <template #default>
                <RuiTab>{{ t('exchange_balances.tabs.balances') }}</RuiTab>
                <RuiTab v-if="exchangeSavingsExist">
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
                    sticky-header
                  />
                </RuiTabItem>
                <RuiTabItem
                  v-if="exchangeSavingsExist && isBinance(exchange)"
                  class="md:pl-4"
                >
                  <BinanceSavingDetail :exchange="exchange" />
                </RuiTabItem>
              </template>
            </RuiTabItems>
          </div>

          <div
            v-else
            class="p-4"
          >
            {{ t('exchange_balances.select_hint') }}
          </div>
        </div>
      </div>
      <div
        v-else
        class="p-2"
      >
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
