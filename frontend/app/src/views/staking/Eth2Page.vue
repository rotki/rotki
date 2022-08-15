<template>
  <div>
    <no-premium-placeholder
      v-if="!premium"
      :text="$t('eth2_page.no_premium')"
    />
    <module-not-active v-else-if="!enabled" :modules="module" />
    <progress-screen v-else-if="loading">
      <template #message>
        {{ $t('eth2_page.loading') }}
      </template>
    </progress-screen>
    <eth2-staking
      v-else
      :refreshing="primaryRefreshing"
      :secondary-refreshing="secondaryRefreshing"
      :validators="eth2Validators"
      :filter-type="filterType"
      :filter="selection"
      :eth2-details="details"
      :eth2-deposits="deposits"
      :eth2-stats="stats"
      :eth2-stats-loading="eth2StatsLoading"
      :ownership="ownership"
      @refresh="refresh"
      @update:stats-pagination="updatePagination"
    >
      <template #selection="{ usableAddresses }">
        <v-row>
          <v-col>
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <div v-bind="attrs" v-on="on">
                  <v-btn-toggle v-model="filterType" dense mandatory>
                    <v-btn value="key">{{ $t('eth2_page.toggle.key') }}</v-btn>
                    <v-btn value="address">
                      {{ $t('eth2_page.toggle.depositor') }}
                    </v-btn>
                  </v-btn-toggle>
                </div>
              </template>
              <span>{{ $t('eth2_page.toggle.hint') }}</span>
            </v-tooltip>
          </v-col>
          <v-col cols="12" md="6">
            <eth2-validator-filter
              v-model="selection"
              :filter-type="filterType"
              :usable-addresses="usableAddresses"
            />
          </v-col>
        </v-row>
      </template>
      <template #modules>
        <active-modules :modules="module" />
      </template>
    </eth2-staking>
  </div>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  onMounted,
  ref,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import Eth2ValidatorFilter from '@/components/helper/filter/Eth2ValidatorFilter.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import { isSectionLoading, setupStatusChecking } from '@/composables/common';
import { getPremium, useModules } from '@/composables/session';
import { Eth2Staking } from '@/premium/premium';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { Section } from '@/store/const';
import { useEth2StakingStore } from '@/store/staking';
import { Module } from '@/types/modules';

const Eth2Page = defineComponent({
  name: 'Eth2Page',
  components: {
    NoPremiumPlaceholder,
    Eth2ValidatorFilter,
    ActiveModules,
    ModuleNotActive,
    ProgressScreen,
    Eth2Staking
  },
  setup() {
    const selection = ref<string[]>([]);
    const filterType = ref<'address' | 'key'>('key');
    const { isModuleEnabled } = useModules();

    const enabled = isModuleEnabled(Module.ETH2);

    const store = useEth2StakingStore();
    const { details, deposits, stats } = storeToRefs(store);
    const { load, updatePagination } = store;

    onMounted(async () => {
      if (get(enabled)) {
        await refresh();
      }
    });
    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const loading = shouldShowLoadingScreen(Section.STAKING_ETH2);
    const primaryRefreshing = isSectionRefreshing(Section.STAKING_ETH2);
    const secondaryRefreshing = isSectionRefreshing(
      Section.STAKING_ETH2_DEPOSITS
    );
    const eth2StatsLoading = isSectionLoading(Section.STAKING_ETH2_STATS);

    const { eth2ValidatorsState: eth2Validators } = storeToRefs(
      useBlockchainAccountsStore()
    );
    watch(filterType, () => set(selection, []));

    const refresh = async () => await load(true);

    const ownership = computed(() => {
      const ownership: Record<string, string> = {};
      for (const { validatorIndex, ownershipPercentage } of get(eth2Validators)
        .entries) {
        ownership[validatorIndex] = ownershipPercentage;
      }
      return ownership;
    });

    return {
      selection,
      loading,
      primaryRefreshing,
      secondaryRefreshing,
      eth2StatsLoading,
      enabled,
      filterType,
      eth2Validators,
      deposits,
      details,
      stats,
      ownership,
      premium: getPremium(),
      refresh,
      updatePagination,
      chains: [Blockchain.ETH],
      module: [Module.ETH2]
    };
  }
});
export default Eth2Page;
</script>
