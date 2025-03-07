<script setup lang="ts">
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';

const { t } = useI18n();

const search = ref<string>('');
const { load } = useExternalApiKeys(t);

const services = [
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/EtherscanApiKeys.vue')),
    name: 'etherscan',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/BlockscoutApiKeys.vue')),
    name: 'blockscout',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/CryptoCompareApiKey.vue')),
    name: 'cryptocompare',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/BeaconchainApiKey.vue')),
    name: 'beaconchain',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/LoopringApiKey.vue')),
    name: 'loopring',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/OpenSeaApiKey.vue')),
    name: 'opensea',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/MoneriumAuth.vue')),
    name: 'monerium',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/TheGraphApiKey.vue')),
    name: 'thegraph',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/GnosisPayAuth.vue')),
    name: 'gnosispay',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/DefiLlamaApiKey.vue')),
    name: 'defillama',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/CoinGeckoApiKey.vue')),
    name: 'coingecko',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/api-keys/external/AlchemyApiKey.vue')),
    name: 'alchemy',
  },
];

// Update the filteredServices computed property
const filteredServices = computed(() => {
  const searchVal = get(search);
  if (!searchVal) {
    return services;
  }
  const keyword = getTextToken(searchVal);
  return services.filter(service => getTextToken(service.name).includes(keyword));
});

onMounted(async () => {
  await load();
});
</script>

<template>
  <TablePageLayout
    data-cy="external-keys"
    :title="[t('navigation_menu.api_keys'), t('navigation_menu.api_keys_sub.external_services')]"
  >
    <template #buttons>
      <RuiTextField
        v-model="search"
        color="primary"
        variant="outlined"
        clearable
        dense
        hide-details
        class="w-[360px]"
        :label="t('external_services.search')"
        prepend-icon="lu-search"
      />
    </template>
    <RuiAlert
      type="info"
      class="my-2"
    >
      {{ t('external_services.subtitle') }}
    </RuiAlert>
    <div class="grid sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-4 sm:gap-6">
      <template v-if="filteredServices.length > 0">
        <Component
          :is="service.component"
          v-for="(service) in filteredServices"
          :key="service.name"
        />
      </template>
      <template v-else>
        <div class="p-4">
          {{ t('external_services.no_services_found') }}
        </div>
      </template>
    </div>
  </TablePageLayout>
</template>
