<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import HistoryEventsView from '@/components/history/events/HistoryEventsView.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import LiquityPools from '@/components/staking/liquity/LiquityPools.vue';
import LiquityStake from '@/components/staking/liquity/LiquityStake.vue';
import LiquityStatistics from '@/components/staking/liquity/LiquityStatistics.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useLiquityStore } from '@/store/defi/liquity';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import { zeroBalance } from '@/utils/bignumbers';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';
import {
  type AssetBalance,
  type Balance,
  Blockchain,
  HistoryEventEntryType,
  type LiquityPoolDetailEntry,
  type LiquityPoolDetails,
  type LiquityStakingDetailEntry,
  type LiquityStakingDetails,
  type LiquityStatisticDetails,
} from '@rotki/common';

const emit = defineEmits<{
  (e: 'refresh', refresh: boolean): void;
}>();

defineSlots<{
  modules: () => any;
}>();

const selectedAccounts = ref<BlockchainAccount<AddressData>[]>([]);
const liquityStore = useLiquityStore();
const { staking, stakingPools, stakingQueryStatus, statistics } = storeToRefs(liquityStore);

const { getProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();
const liquityHistoricPriceStatus = getProtocolStatsPriceQueryStatus('liquity');

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STAKING);

const chains = [Blockchain.ETH];

const { t } = useI18n();

const accountFilter = useArrayMap(selectedAccounts, account => ({
  address: getAccountAddress(account),
  chain: account.chain,
}));

const aggregatedStake = computed<LiquityStakingDetailEntry | null>(() => {
  const allStakes: LiquityStakingDetails = get(staking);
  const selectedAddresses = get(selectedAccounts).map(account => getAccountAddress(account));

  const filteredStakes: LiquityStakingDetailEntry[] = [];

  for (const address in allStakes) {
    const stake = allStakes[address];
    if (selectedAddresses.length > 0 && !selectedAddresses.includes(address))
      continue;

    if (stake.balances)
      filteredStakes.push(stake.balances);

    if (stake.proxies)
      filteredStakes.push(...Object.values(stake.proxies));
  }

  let stakes: LiquityStakingDetailEntry | null = null;

  filteredStakes.forEach((stake) => {
    if (stakes === null) {
      stakes = { ...stake };
    }
    else {
      let key: keyof LiquityStakingDetailEntry;
      for (key in stakes) {
        stakes[key] = {
          ...stakes[key],
          ...balanceSum(stakes[key], stake[key]),
        };
      }
    }
  });
  return stakes;
});

const aggregatedStakingPool = computed<LiquityPoolDetailEntry | null>(() => {
  const allPools: LiquityPoolDetails = get(stakingPools);
  const selectedAddresses = get(selectedAccounts).map(account => getAccountAddress(account));
  const filteredPools: LiquityPoolDetailEntry[] = [];

  for (const address in allPools) {
    const pool = allPools[address];
    if (selectedAddresses.length > 0 && !selectedAddresses.includes(address))
      continue;

    if (pool.balances)
      filteredPools.push(pool.balances);

    if (pool.proxies)
      filteredPools.push(...Object.values(pool.proxies));
  }

  let pools: LiquityPoolDetailEntry | null = null;
  filteredPools.forEach((pool) => {
    if (pools === null) {
      pools = { ...pool };
    }
    else {
      let key: keyof LiquityPoolDetailEntry;
      for (key in pools) {
        pools[key] = {
          ...pools[key],
          ...balanceSum(pools[key], pool[key]),
        };
      }
    }
  });

  return pools;
});

const proxyInformation = computed<Record<string, string[]> | null>(() => {
  const proxies: Record<string, string[]> = {};
  const allStakes: LiquityStakingDetails = get(staking);
  const allPools: LiquityPoolDetails = get(stakingPools);

  const selectedAddresses = get(selectedAccounts).map(account => getAccountAddress(account));

  const addToProxies = (mainAddress: string, proxyAddresses: string[]) => {
    if (!proxies[mainAddress])
      proxies[mainAddress] = proxyAddresses;
    else
      proxies[mainAddress] = [...proxies[mainAddress], ...proxyAddresses].filter(uniqueStrings);
  };

  selectedAddresses.forEach((address) => {
    const pool = allPools[address];
    if (pool && pool.proxies) {
      const poolProxies = Object.keys(pool.proxies);
      if (poolProxies.length > 0)
        addToProxies(address, poolProxies);
    }

    const stake = allStakes[address];
    if (stake && stake.proxies) {
      const stakeProxies = Object.keys(stake.proxies);
      if (stakeProxies.length > 0)
        addToProxies(address, stakeProxies);
    }
  });

  if (Object.keys(proxies).length === 0)
    return null;

  return proxies;
});

const aggregatedStatistic = computed<LiquityStatisticDetails | null>(() => {
  const allStatistics = get(statistics);

  if (!allStatistics)
    return null;

  const selectedAddresses = get(selectedAccounts).map(account => getAccountAddress(account));

  if (selectedAddresses.length === 0)
    return allStatistics.globalStats ?? null;

  if (!allStatistics.byAddress)
    return null;

  let aggregatedStatistic: LiquityStatisticDetails | null = null;
  for (const address in allStatistics.byAddress) {
    if (!selectedAddresses.includes(address))
      continue;

    const statistic = allStatistics.byAddress[address];
    if (aggregatedStatistic === null) {
      aggregatedStatistic = { ...statistic };
    }
    else {
      const { stabilityPoolGains, stakingGains, ...remaining } = statistic;

      let key: keyof typeof remaining;

      for (key in remaining)
        aggregatedStatistic[key] = aggregatedStatistic[key].plus(remaining[key]);

      const mergeAssetBalances = (items1: AssetBalance[], items2: AssetBalance[]) => {
        const aggregated = [...items1, ...items2];

        const uniqueAssets = aggregated.map(({ asset }) => asset).filter(uniqueStrings);

        return uniqueAssets.map(asset => ({
          asset,
          ...aggregated
            .filter((item: AssetBalance) => asset === item.asset)
            .reduce((previous: Balance, current: Balance) => balanceSum(previous, current), zeroBalance()),
        }));
      };

      aggregatedStatistic.stakingGains = mergeAssetBalances(aggregatedStatistic.stakingGains, stakingGains);
      aggregatedStatistic.stabilityPoolGains = mergeAssetBalances(
        aggregatedStatistic.stabilityPoolGains,
        stabilityPoolGains,
      );
    }
  }

  return aggregatedStatistic;
});

const availableAddresses = computed(() =>
  [...Object.keys(get(staking)), ...Object.keys(get(stakingPools))].filter(uniqueStrings),
);

function refresh() {
  emit('refresh', true);
}
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking.liquity')]"
    child
  >
    <template #buttons>
      <div class="flex items-center gap-3">
        <div v-if="$slots.modules">
          <slot name="modules" />
        </div>
        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              variant="outlined"
              color="primary"
              :loading="loading"
              @click="refresh()"
            >
              <template #prepend>
                <RuiIcon name="lu-refresh-ccw" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ t('liquity_staking_details.refresh_tooltip') }}
        </RuiTooltip>
      </div>
    </template>
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <BlockchainAccountSelector
        v-model="selectedAccounts"
        :label="t('liquity_staking_details.select_account')"
        :chains="chains"
        dense
        outlined
        :usable-addresses="availableAddresses"
      />

      <div
        v-if="proxyInformation || loading"
        class="flex flex-wrap items-center gap-2"
      >
        <RuiMenu
          v-if="proxyInformation"
          :popper="{ placement: 'right-start' }"
          menu-class="max-w-[25rem]"
        >
          <template #activator="{ attrs }">
            <RuiButton
              variant="text"
              class="!p-2"
              icon
              v-bind="attrs"
            >
              <RuiIcon name="lu-info" />
            </RuiButton>
          </template>
          <div class="p-3 px-4">
            <div
              v-for="(proxies, key, index) in proxyInformation"
              :key="key"
            >
              <div class="flex flex-row items-center gap-2">
                <HashLink
                  :text="key"
                  class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 rounded-full m-0.5"
                />
                <span class="text-sm">
                  {{
                    t('liquity_staking_details.has_proxy_addresses', {
                      length: proxies.length,
                    })
                  }}
                </span>
              </div>
              <div
                class="ml-3 pl-4 pt-2"
                :class="$style['proxies-wrapper']"
              >
                <div
                  v-for="proxy in proxies"
                  :key="proxy"
                  class="mb-1 flex"
                  :class="$style['proxies-item']"
                >
                  <HashLink
                    :text="proxy"
                    class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 rounded-full m-0.5"
                  />
                </div>
              </div>
              <RuiDivider
                v-if="index < Object.keys(proxyInformation).length - 1"
                class="my-4"
              />
            </div>
          </div>
        </RuiMenu>

        <div
          v-if="loading && (stakingQueryStatus || liquityHistoricPriceStatus)"
          class="flex items-center gap-3 text-rui-text-secondary text-sm"
        >
          <RuiProgress
            thickness="2"
            size="18"
            color="primary"
            variant="indeterminate"
            circular
          />
          <div>
            <div v-if="stakingQueryStatus">
              {{
                t('liquity_staking_details.query_staking_data', {
                  processed: stakingQueryStatus.processed,
                  total: stakingQueryStatus.total,
                })
              }}
            </div>

            <div v-if="liquityHistoricPriceStatus">
              {{
                t('liquity_staking_details.query_historical_price', {
                  processed: liquityHistoricPriceStatus.processed,
                  total: liquityHistoricPriceStatus.total,
                })
              }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="grid md:grid-cols-2 gap-4">
      <LiquityPools
        class="flex-1"
        :pool="aggregatedStakingPool"
      />
      <LiquityStake
        class="flex-1"
        :stake="aggregatedStake"
      />
    </div>

    <LiquityStatistics
      :statistic="aggregatedStatistic"
      :pool="aggregatedStakingPool"
    />

    <HistoryEventsView
      use-external-account-filter
      :section-title="t('liquity_staking_events.title')"
      :protocols="['liquity']"
      :external-account-filter="accountFilter"
      :only-chains="chains"
      :entry-types="[HistoryEventEntryType.EVM_EVENT]"
    />
  </TablePageLayout>
</template>

<style lang="scss" module>
.proxies {
  &-wrapper,
  &-item {
    &::before {
      @apply border-rui-grey-200;
    }
  }

  &-wrapper {
    @apply relative;

    &::before {
      @apply absolute top-0 left-0 border-l;
      content: '';
      height: calc(100% - 0.8rem);
    }
  }

  &-item {
    @apply relative;

    &::before {
      @apply absolute w-4 right-full top-1/2 border-t;
      content: '';
    }
  }
}

:global(.dark) {
  .proxies {
    &-wrapper,
    &-item {
      &::before {
        @apply border-rui-grey-800;
      }
    }
  }
}
</style>
