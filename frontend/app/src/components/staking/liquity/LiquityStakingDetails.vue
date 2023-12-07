<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  type LiquityPoolDetailEntry,
  type LiquityPoolDetails,
  type LiquityStakingDetailEntry,
  type LiquityStakingDetails,
  type LiquityStatisticDetails
} from '@rotki/common/lib/liquity';
import { type ComputedRef, type Ref } from 'vue';
import { type AssetBalance, type Balance } from '@rotki/common';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { Section } from '@/types/status';

const emit = defineEmits<{
  (e: 'refresh', refresh: boolean): void;
}>();

const selectedAccounts: Ref<GeneralAccount[]> = ref([]);
const liquityStore = useLiquityStore();
const { staking, stakingPools, statistics } = toRefs(liquityStore);

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STAKING);

const chains = [Blockchain.ETH];

const { t } = useI18n();

const aggregatedStake: ComputedRef<LiquityStakingDetailEntry | null> = computed(
  () => {
    const allStakes: LiquityStakingDetails = get(staking);
    const selectedAddresses = get(selectedAccounts).map(
      ({ address }) => address
    );

    const filteredStakes: LiquityStakingDetailEntry[] = [];

    for (const address in allStakes) {
      const stake = allStakes[address];
      if (
        selectedAddresses.length > 0 &&
        !selectedAddresses.includes(address)
      ) {
        continue;
      }

      if (stake.balances) {
        filteredStakes.push(stake.balances);
      }

      if (stake.proxies) {
        filteredStakes.push(...Object.values(stake.proxies));
      }
    }

    let stakes: LiquityStakingDetailEntry | null = null;

    filteredStakes.forEach(stake => {
      if (stakes === null) {
        stakes = { ...stake };
      } else {
        let key: keyof LiquityStakingDetailEntry;
        for (key in stakes) {
          stakes[key] = {
            ...stakes[key],
            ...balanceSum(stakes[key], stake[key])
          };
        }
      }
    });
    return stakes;
  }
);

const aggregatedStakingPool: ComputedRef<LiquityPoolDetailEntry | null> =
  computed(() => {
    const allPools: LiquityPoolDetails = get(stakingPools);

    const selectedAddresses = get(selectedAccounts).map(
      ({ address }) => address
    );

    const filteredPools: LiquityPoolDetailEntry[] = [];

    for (const address in allPools) {
      const pool = allPools[address];
      if (
        selectedAddresses.length > 0 &&
        !selectedAddresses.includes(address)
      ) {
        continue;
      }

      if (pool.balances) {
        filteredPools.push(pool.balances);
      }

      if (pool.proxies) {
        filteredPools.push(...Object.values(pool.proxies));
      }
    }

    let pools: LiquityPoolDetailEntry | null = null;
    filteredPools.forEach(pool => {
      if (pools === null) {
        pools = { ...pool };
      } else {
        let key: keyof LiquityPoolDetailEntry;
        for (key in pools) {
          pools[key] = {
            ...pools[key],
            ...balanceSum(pools[key], pool[key])
          };
        }
      }
    });

    return pools;
  });

const proxyInformation: ComputedRef<Record<string, string[]> | null> = computed(
  () => {
    const proxies: Record<string, string[]> = {};
    const allStakes: LiquityStakingDetails = get(staking);
    const allPools: LiquityPoolDetails = get(stakingPools);

    const selectedAddresses = get(selectedAccounts).map(
      ({ address }) => address
    );

    const addToProxies = (mainAddress: string, proxyAddresses: string[]) => {
      if (!proxies[mainAddress]) {
        proxies[mainAddress] = proxyAddresses;
      } else {
        proxies[mainAddress] = [
          ...proxies[mainAddress],
          ...proxyAddresses
        ].filter(uniqueStrings);
      }
    };

    selectedAddresses.forEach(address => {
      const pool = allPools[address];
      if (pool && pool.proxies) {
        const poolProxies = Object.keys(pool.proxies);
        if (poolProxies.length > 0) {
          addToProxies(address, poolProxies);
        }
      }

      const stake = allStakes[address];
      if (stake && stake.proxies) {
        const stakeProxies = Object.keys(stake.proxies);
        if (stakeProxies.length > 0) {
          addToProxies(address, stakeProxies);
        }
      }
    });

    if (Object.keys(proxies).length === 0) {
      return null;
    }

    return proxies;
  }
);

const aggregatedStatistic: ComputedRef<LiquityStatisticDetails | null> =
  computed(() => {
    const allStatistics = get(statistics);

    if (!allStatistics) {
      return null;
    }

    const selectedAddresses = get(selectedAccounts).map(
      ({ address }) => address
    );

    if (selectedAddresses.length === 0) {
      return allStatistics.globalStats ?? null;
    }

    if (!allStatistics.byAddress) {
      return null;
    }

    let aggregatedStatistic: LiquityStatisticDetails | null = null;
    for (const address in allStatistics.byAddress) {
      if (!selectedAddresses.includes(address)) {
        continue;
      }

      const statistic = allStatistics.byAddress[address];
      if (aggregatedStatistic === null) {
        aggregatedStatistic = { ...statistic };
      } else {
        const { stakingGains, stabilityPoolGains, ...remaining } = statistic;

        let key: keyof typeof remaining;

        for (key in remaining) {
          aggregatedStatistic[key] = aggregatedStatistic[key].plus(
            remaining[key]
          );
        }

        const mergeAssetBalances = (
          items1: AssetBalance[],
          items2: AssetBalance[]
        ) => {
          const aggregated = [...items1, ...items2];

          const uniqueAssets = aggregated
            .map(({ asset }) => asset)
            .filter(uniqueStrings);

          return uniqueAssets.map(asset => ({
            asset,
            ...aggregated
              .filter((item: AssetBalance) => asset === item.asset)
              .reduce(
                (previous: Balance, current: Balance) =>
                  balanceSum(previous, current),
                zeroBalance()
              )
          }));
        };

        aggregatedStatistic.stakingGains = mergeAssetBalances(
          aggregatedStatistic.stakingGains,
          stakingGains
        );
        aggregatedStatistic.stabilityPoolGains = mergeAssetBalances(
          aggregatedStatistic.stabilityPoolGains,
          stabilityPoolGains
        );
      }
    }

    return aggregatedStatistic;
  });

const availableAddresses = computed(() =>
  [...Object.keys(get(staking)), ...Object.keys(get(stakingPools))].filter(
    uniqueStrings
  )
);

const refresh = async () => {
  emit('refresh', true);
};

const css = useCssModule();
const slots = useSlots();
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking.liquity')]"
    child
  >
    <template #buttons>
      <div class="flex items-center gap-3">
        <div v-if="slots.modules">
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
                <RuiIcon name="refresh-line" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ t('liquity_staking_details.refresh_tooltip') }}
        </RuiTooltip>
      </div>
    </template>
    <div class="flex gap-4 items-start">
      <BlockchainAccountSelector
        v-model="selectedAccounts"
        :label="t('liquity_staking_details.select_account')"
        :chains="chains"
        class="md:w-[25rem]"
        dense
        outlined
        no-padding
        multiple
        flat
        :usable-addresses="availableAddresses"
      />

      <VMenu v-if="proxyInformation" offset-x nudge-right="8" min-width="410">
        <template #activator="{ on, attrs }">
          <RuiButton variant="text" class="!p-2" icon v-bind="attrs" v-on="on">
            <RuiIcon name="information-line" />
          </RuiButton>
        </template>
        <div class="pa-4">
          <div v-for="(proxies, key, index) in proxyInformation" :key="key">
            <div class="flex flex-row items-center gap-2">
              <RuiChip>
                <HashLink :text="key" />
              </RuiChip>
              {{
                t('liquity_staking_details.has_proxy_addresses', {
                  length: proxies.length
                })
              }}
            </div>
            <div class="ml-4 pl-4 pt-2" :class="css['proxies-wrapper']">
              <div
                v-for="proxy in proxies"
                :key="proxy"
                class="mb-1"
                :class="css['proxies-item']"
              >
                <RuiChip class="pl-1 pr-2">
                  <HashLink :text="proxy" />
                </RuiChip>
              </div>
            </div>
            <RuiDivider
              v-if="index < Object.keys(proxyInformation).length - 1"
              class="my-4"
            />
          </div>
        </div>
      </VMenu>
    </div>

    <div class="flex flex-row flex-wrap gap-4">
      <LiquityPools class="flex-1" :pool="aggregatedStakingPool" />
      <LiquityStake class="flex-1" :stake="aggregatedStake" />
    </div>

    <LiquityStatistics
      :statistic="aggregatedStatistic"
      :pool="aggregatedStakingPool"
    />

    <HistoryEventsView
      use-external-account-filter
      :section-title="t('liquity_staking_events.title')"
      :protocols="['liquity']"
      :external-account-filter="selectedAccounts"
      :only-chains="chains"
      :entry-types="[HistoryEventEntryType.EVM_EVENT]"
    />
  </TablePageLayout>
</template>

<style lang="scss" module>
.proxies {
  &-wrapper {
    position: relative;

    &::before {
      content: '';
      position: absolute;
      height: calc(100% - 1.1rem);
      top: 0;
      left: 0;
      border-left: 1px solid var(--border-color);
    }
  }

  &-item {
    position: relative;

    &::before {
      position: absolute;
      content: '';
      width: 1rem;
      right: 100%;
      top: 50%;
      border-top: 1px solid var(--border-color);
    }
  }
}
</style>
