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
import { Section } from '@/types/status';

const selectedAccounts: Ref<GeneralAccount[]> = ref([]);
const liquityStore = useLiquityStore();
const { staking, stakingPools, statistics } = toRefs(liquityStore);

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STAKING);

const chains = [Blockchain.ETH];

const { tc } = useI18n();

const emit = defineEmits<{
  (e: 'refresh', refresh: boolean): void;
}>();

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
        let key: keyof typeof stakes;
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
        let key: keyof typeof pools;
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
      return allStatistics.globalStats;
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
</script>

<template>
  <div>
    <v-row align="center" class="pt-2">
      <v-col sm="6" cols="10">
        <blockchain-account-selector
          v-model="selectedAccounts"
          :label="tc('liquity_staking_details.select_account')"
          :chains="chains"
          dense
          outlined
          no-padding
          multiple
          flat
          :usable-addresses="availableAddresses"
        />
      </v-col>
      <v-col>
        <v-menu
          v-if="proxyInformation"
          offset-x
          nudge-right="8"
          min-width="410"
        >
          <template #activator="{ on, attrs }">
            <v-icon v-bind="attrs" v-on="on"> mdi-information</v-icon>
          </template>
          <div class="pa-4">
            <div v-for="(proxies, key, index) in proxyInformation" :key="key">
              <div class="d-flex align-center">
                <v-chip class="pl-1 pr-2">
                  <hash-link :text="key" />
                </v-chip>
                <div class="ml-2">
                  {{
                    tc('liquity_staking_details.has_proxy_addresses', 0, {
                      length: proxies.length
                    })
                  }}
                </div>
              </div>
              <div class="ml-4 pl-4 pt-2" :class="css['proxies-wrapper']">
                <div
                  v-for="proxy in proxies"
                  :key="proxy"
                  class="mb-1"
                  :class="css['proxies-item']"
                >
                  <v-chip class="pl-1 pr-2">
                    <hash-link :text="proxy" />
                  </v-chip>
                </div>
              </div>
              <v-divider
                v-if="index < Object.keys(proxyInformation).length - 1"
                class="my-4"
              />
            </div>
          </div>
        </v-menu>
      </v-col>
      <v-col v-if="$slots.modules" cols="auto">
        <slot name="modules" />
      </v-col>
      <v-col cols="auto" class="pl-2">
        <refresh-button
          :tooltip="tc('liquity_staking_details.refresh_tooltip')"
          :loading="loading"
          @refresh="refresh"
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col md="6" cols="12">
        <liquity-pools :pool="aggregatedStakingPool" />
      </v-col>

      <v-col md="6" cols="12">
        <liquity-stake :stake="aggregatedStake" />
      </v-col>

      <v-col>
        <liquity-statistics
          :statistic="aggregatedStatistic"
          :pool="aggregatedStakingPool"
        />
      </v-col>
    </v-row>

    <history-events-view
      use-external-account-filter
      :section-title="tc('liquity_staking_events.title')"
      :protocols="['liquity']"
      :external-account-filter="selectedAccounts"
      :only-chains="chains"
    />
  </div>
</template>
<style lang="scss" module>
.proxies {
  &-wrapper {
    position: relative;

    &::before {
      content: '';
      position: absolute;
      height: calc(100% - 1rem);
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
