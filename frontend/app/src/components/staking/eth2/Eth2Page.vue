<script setup lang="ts">
import { Eth2Staking } from '@/premium/premium';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const selection = ref<string[]>([]);
const filterType = ref<'address' | 'key'>('key');
const { isModuleEnabled } = useModules();

const enabled = isModuleEnabled(Module.ETH2);

const store = useEth2StakingStore();
const { details, stats } = storeToRefs(store);
const { load, updatePagination } = store;

onMounted(async () => {
  if (get(enabled)) {
    await load(false);
    await refresh();
  }
});

onUnmounted(() => {
  store.$reset();
});

const { isLoading, shouldShowLoadingScreen } = useStatusStore();

const loading = shouldShowLoadingScreen(Section.STAKING_ETH2);
const primaryRefreshing = isLoading(Section.STAKING_ETH2);
const secondaryRefreshing = isLoading(Section.STAKING_ETH2_DEPOSITS);

const eth2StatsLoading = isLoading(Section.STAKING_ETH2_STATS);

const { eth2Validators } = storeToRefs(useEthAccountsStore());
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

const premium = usePremium();

const module = [Module.ETH2];

const { t, tc } = useI18n();
</script>

<template>
  <div>
    <no-premium-placeholder
      v-if="!premium"
      :text="tc('eth2_page.no_premium')"
    />
    <module-not-active v-else-if="!enabled" :modules="module" />
    <progress-screen v-else-if="loading">
      <template #message>
        {{ t('eth2_page.loading') }}
      </template>
    </progress-screen>
    <eth2-staking
      v-else
      :refreshing="primaryRefreshing"
      :secondary-refreshing="secondaryRefreshing"
      :validators="eth2Validators.entries"
      :filter-type="filterType"
      :filter="selection"
      :eth2-details="details"
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
                    <v-btn value="key">{{ t('eth2_page.toggle.key') }}</v-btn>
                    <v-btn value="address">
                      {{ t('eth2_page.toggle.depositor') }}
                    </v-btn>
                  </v-btn-toggle>
                </div>
              </template>
              <span>{{ t('eth2_page.toggle.hint') }}</span>
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
