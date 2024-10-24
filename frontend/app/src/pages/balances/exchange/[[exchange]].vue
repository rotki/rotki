<script setup lang="ts">
import { Routes } from '@/router/routes';
import { TaskType } from '@/types/task-type';
import { NoteLocation } from '@/types/notes';
import type { BigNumber } from '@rotki/common';
import type { AssetBalanceWithPrice } from '@/types/balances';

definePage({
  name: 'accounts-balances-exchange',
  meta: {
    noteLocation: NoteLocation.ACCOUNTS_BALANCES_EXCHANGE,
  },
  props: true,
});

const props = defineProps<{ exchange?: string }>();

const { t } = useI18n();
const selectedTab = ref<string | undefined>(props.exchange ?? undefined);

const { exchange } = toRefs(props);
const { isTaskRunning } = useTaskStore();
const { getBalances, refreshExchangeSavings, fetchExchangeSavings } = useExchangeBalancesStore();
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
  set(selectedExchange, get(route).query.location);
}

onMounted(() => {
  setSelectedExchange();
});

watch(route, () => {
  setSelectedExchange();
});

function exchangeBalance(exchange: string): BigNumber {
  const balances = get(getBalances(exchange));
  return balances.reduce((sum, asset: AssetBalanceWithPrice) => sum.plus(asset.value), Zero);
}

const sortedExchanges = computed(() =>
  get(usedExchanges).sort((a, b) => exchangeBalance(b).minus(exchangeBalance(a)).toNumber()),
);

function openExchangeDetails() {
  router.push({
    name: 'accounts-balances-exchange',
    params: {
      exchange: get(selectedExchange),
    },
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
    path: '/api-keys/exchanges',
    query: { add: 'true' },
  });
}

const exchangeSavingsExist = ref<boolean>(false);
const exchangeDetailTabs = ref<number>(0);

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

function isBinance(exchange?: string): exchange is 'binance' | 'binanceus' {
  return !!exchange && ['binance', 'binanceus'].includes(exchange);
}
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.accounts_balances'), t('exchange_balances.title')]">
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
            hide-details
            variant="outlined"
            @update:model-value="openExchangeDetails()"
          >
            <template #selection="{ item }">
              <ExchangeAmountRow
                class="pr-3 py-1"
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
          </RuiMenuSelect>
        </div>
        <div class="hidden md:block w-1/6 border-r border-default">
          <RuiTabs
            v-model="selectedTab"
            vertical
            color="primary"
          >
            <RuiTab
              v-for="(usedExchange, i) in sortedExchanges"
              :key="i"
              link
              class="h-[8rem]"
              :to="{
                name: 'accounts-balances-exchange',
                params: {
                  exchange: usedExchange,
                },
              }"
              :model-value="usedExchange"
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
          </RuiTabs>
        </div>
        <div class="flex-1">
          <div v-if="exchange">
            <RuiTabs
              v-model="exchangeDetailTabs"
              color="primary"
            >
              <RuiTab>{{ t('exchange_balances.tabs.balances') }}</RuiTab>
              <RuiTab v-if="exchangeSavingsExist">
                {{ t('exchange_balances.tabs.savings_interest_history') }}
              </RuiTab>
            </RuiTabs>

            <RuiDivider />

            <RuiTabItems v-model="exchangeDetailTabs">
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
        <i18n-t
          keypath="exchange_balances.no_connected_exchanges"
          tag="span"
        >
          <InternalLink
            :to="Routes.API_KEYS_EXCHANGES"
            class="module-not-active__link font-weight-regular text-body-1 text-decoration-none"
          >
            {{ t('exchange_balances.click_here') }}
          </InternalLink>
        </i18n-t>
      </div>
    </RuiCard>
  </TablePageLayout>
</template>
