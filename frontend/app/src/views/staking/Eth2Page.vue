<template>
  <div>
    <module-not-active v-if="!enabled" :modules="module" />
    <progress-screen v-else-if="loading">
      <template #message>
        {{ $t('eth2page.loading') }}
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
  Eth2DailyStats,
  Eth2DailyStatsPayload,
  Eth2Deposits,
  Eth2Details
} from '@rotki/common/lib/staking/eth2';
import {
  computed,
  defineComponent,
  onMounted,
  ref,
  watch
} from '@vue/composition-api';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import Eth2ValidatorFilter from '@/components/helper/filter/Eth2ValidatorFilter.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupBlockchainAccounts } from '@/composables/balances';
import { setupStatusChecking } from '@/composables/common';
import { setupModuleEnabled } from '@/composables/session';
import { setupStaking } from '@/composables/staking';
import { Eth2Staking } from '@/premium/premium';
import { Section } from '@/store/const';
import { useStore } from '@/store/utils';
import { Module } from '@/types/modules';
import { assert } from '@/utils/assertions';

const Eth2Page = defineComponent({
  name: 'Eth2Page',
  components: {
    Eth2ValidatorFilter,
    ActiveModules,
    ModuleNotActive,
    ProgressScreen,
    Eth2Staking
  },
  setup() {
    const selection = ref<string[]>([]);
    const filterType = ref<'address' | 'key'>('key');
    const { isModuleEnabled } = setupModuleEnabled();

    const enabled = isModuleEnabled(Module.ETH2);
    const { fetchEth2StakingDetails } = setupStaking();

    onMounted(async () => {
      if (enabled.value) {
        await fetchEth2StakingDetails();
      }
    });
    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const loading = shouldShowLoadingScreen(Section.STAKING_ETH2);
    const primaryRefreshing = isSectionRefreshing(Section.STAKING_ETH2);
    const secondaryRefreshing = isSectionRefreshing(
      Section.STAKING_ETH2_DEPOSITS
    );

    const { eth2Validators } = setupBlockchainAccounts();
    watch(filterType, () => (selection.value = []));

    const store = useStore();
    const deposits = computed<Eth2Deposits>(
      () => store.getters['staking/deposits']
    );
    const details = computed<Eth2Details>(
      () => store.getters['staking/details']
    );
    const stats = computed<Eth2DailyStats>(
      () => store.getters['staking/stats']
    );

    const refresh = async () => {
      await store.dispatch('staking/fetchStakingDetails', true);
    };

    const updatePagination = async (payload: Eth2DailyStatsPayload) => {
      await store.dispatch('staking/fetchDailyStats', payload);
    };

    const ownership = computed(() => {
      const balances = store.state.balances;
      const ownership: Record<string, string> = {};
      assert(balances);
      for (const { validatorIndex, ownershipPercentage } of balances
        .eth2Validators.entries) {
        ownership[validatorIndex] = ownershipPercentage;
      }
      return ownership;
    });

    return {
      selection,
      loading,
      primaryRefreshing,
      secondaryRefreshing,
      enabled,
      filterType,
      eth2Validators,
      deposits,
      details,
      stats,
      ownership,
      refresh,
      updatePagination,
      chains: [Blockchain.ETH],
      module: [Module.ETH2]
    };
  }
});
export default Eth2Page;
</script>
