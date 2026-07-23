<script setup lang="ts">
import { type AssetBalanceWithPrice, type BigNumber, Zero } from '@rotki/common';
import { msg } from '@/message-key';
import ExchangeAmountRow from '@/modules/accounts/exchanges/ExchangeAmountRow.vue';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import ExchangeDetailPanel from '@/modules/balances/exchanges/ExchangeDetailPanel.vue';
import { useBinanceSavings } from '@/modules/balances/exchanges/use-binance-savings';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { NoteLocation } from '@/modules/core/common/notes';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import HideSmallBalances from '@/modules/settings/HideSmallBalances.vue';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import InternalLink from '@/modules/shell/components/InternalLink.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.exchange_balances'), icon: 'lu-coins-exchange', parent: '/balances/', order: 20, drawer: 'balances-exchange' },
    noteLocation: NoteLocation.BALANCES_EXCHANGE,
  },
  props: true,
});

const { exchange } = defineProps<{ exchange?: string }>();

const { t } = useI18n({ useScope: 'global' });
const selectedTab = ref<string | undefined>(exchange ?? undefined);
const { useIsTaskRunning } = useTaskStore();
const { getExchangeBalances } = useAggregatedBalances();
const { refreshExchangeSavings } = useBinanceSavings();
const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());

const { refreshBalance, refreshExchangeBalance } = useBalanceRefresh();

async function refreshExchangeBalances() {
  await Promise.all([refreshBalance('exchange'), refreshExchangeSavings(true)]);
}

async function refreshSelectedExchangeBalances(exchangeLocation: string) {
  if (isBinance(exchangeLocation))
    await Promise.all([refreshExchangeBalance(exchangeLocation), refreshExchangeSavings(true)]);
  else
    await refreshExchangeBalance(exchangeLocation);
}
const selectedExchange = ref<string>('');
const usedExchanges = computed<string[]>(() =>
  get(connectedExchanges)
    .map(({ location }) => location)
    .filter(uniqueStrings),
);

const isExchangeLoading = useIsTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);

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
  const balances = getExchangeBalances(exchange);
  return balances.reduce((sum, asset: AssetBalanceWithPrice) => sum.plus(asset.value), Zero);
}

const sortedExchanges = computed(() =>
  get(usedExchanges).sort((a, b) => exchangeBalance(b).minus(exchangeBalance(a)).toNumber()),
);

function openExchangeDetails() {
  router.push({
    name: '/balances/exchange/[[exchange]]',
    params: {
      exchange: get(selectedExchange),
    },
  });
}

const balances = computed(() => {
  const currentExchange = exchange;
  if (!currentExchange)
    return [];

  return getExchangeBalances(currentExchange);
});

const vueRouter = useRouter();

function navigate() {
  vueRouter.push({
    path: '/api-keys/exchanges',
    query: { add: 'true' },
  });
}

const exchangeDetailTabs = ref<number>(0);

watch(() => exchange, () => {
  set(exchangeDetailTabs, 0);
});

onMounted(() => {
  refreshExchangeSavings();
});

function isBinance(exchange?: string): exchange is 'binance' | 'binanceus' {
  return !!exchange && ['binance', 'binanceus'].includes(exchange);
}
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.exchange_balances')]">
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            size="lg"
            class="exchange-balances__refresh"
            :disabled="exchangeDetailTabs !== 0"
            :loading="isExchangeLoading"
            @click="refreshExchangeBalances()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('exchange_balances.refresh_tooltip') }}
      </RuiTooltip>
      <RuiButton
        color="primary"
        size="lg"
        @click="navigate()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('exchange_balances.add_exchange') }}
      </RuiButton>
      <HideSmallBalances :source="BalanceSource.EXCHANGES" />
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
        <div class="hidden md:block w-40 shrink-0 border-r border-default">
          <RuiTabs
            v-model="selectedTab"
            vertical
            align="end"
            color="primary"
            class="!flex w-full"
          >
            <RuiTab
              v-for="(usedExchange, i) in sortedExchanges"
              :key="i"
              link
              class="h-[8rem]"
              :to="{
                name: '/balances/exchange/[[exchange]]',
                params: {
                  exchange: usedExchange,
                },
              }"
              :model-value="usedExchange"
            >
              <div class="flex flex-col items-center gap-1 pr-2">
                <LocationDisplay
                  :open-details="false"
                  :identifier="usedExchange"
                  size="36px"
                />
                <FiatDisplay
                  class="text-xl"
                  :value="exchangeBalance(usedExchange)"
                />
              </div>
            </RuiTab>
          </RuiTabs>
        </div>
        <div class="flex-1">
          <ExchangeDetailPanel
            v-if="exchange"
            v-model="exchangeDetailTabs"
            :exchange="exchange"
            :loading="isExchangeLoading"
            :balances="balances"
            @refresh="refreshSelectedExchangeBalances($event)"
          />

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
          scope="global"
          keypath="exchange_balances.no_connected_exchanges"
          tag="span"
        >
          <InternalLink
            :to="{
              name: '/api-keys/exchanges/',
              query: { add: 'true' },
            }"
            class="module-not-active__link font-weight-regular text-body-1 text-decoration-none"
          >
            {{ t('exchange_balances.click_here') }}
          </InternalLink>
        </i18n-t>
      </div>
    </RuiCard>
  </TablePageLayout>
</template>
