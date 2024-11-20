<script setup lang="ts">
const { t } = useI18n();

const search = ref<string>('');

const services = {
  etherscan: defineAsyncComponent(() => import('@/components/settings/api-keys/external/EtherscanApiKeys.vue')),
  blockscout: defineAsyncComponent(() => import('@/components/settings/api-keys/external/BlockscoutApiKeys.vue')),
  cryptocompare: defineAsyncComponent(() => import('@/components/settings/api-keys/external/CryptoCompareApiKey.vue')),
  beaconchain: defineAsyncComponent(() => import('@/components/settings/api-keys/external/BeaconchainApiKey.vue')),
  loopring: defineAsyncComponent(() => import('@/components/settings/api-keys/external/LoopringApiKey.vue')),
  opensea: defineAsyncComponent(() => import('@/components/settings/api-keys/external/OpenSeaApiKey.vue')),
  monerium: defineAsyncComponent(() => import('@/components/settings/api-keys/external/MoneriumAuth.vue')),
  thegraph: defineAsyncComponent(() => import('@/components/settings/api-keys/external/TheGraphApiKey.vue')),
  gnosispay: defineAsyncComponent(() => import('@/components/settings/api-keys/external/GnosisPayAuth.vue')),
  defillama: defineAsyncComponent(() => import('@/components/settings/api-keys/external/DefiLlamaApiKey.vue')),
  coingecko: defineAsyncComponent(() => import('@/components/settings/api-keys/external/CoinGeckoApiKey.vue')),
};

const { load } = useExternalApiKeys(t);

const filteredServices = computed(() => {
  const searchVal = get(search);
  if (!searchVal) {
    return Object.values(services);
  }
  const keyword = getTextToken(searchVal);
  return Object.keys(services)
    .filter(key => getTextToken(key).includes(keyword))
    .map(key => services[key as keyof typeof services]);
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
        prepend-icon="search-line"
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
          :is="component"
          v-for="(component, index) in filteredServices"
          :key="index"
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
