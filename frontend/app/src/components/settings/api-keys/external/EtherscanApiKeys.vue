<script setup lang="ts">
import type ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';

const { t } = useI18n();
const { keys } = useExternalApiKeys(t);
const tabIndex = ref<number>(0);
const route = useRoute();
const serviceKeyCardRef = ref<InstanceType<typeof ServiceKeyCard>>();

const { getChainName } = useSupportedChains();

const supportedChains = computed(() => {
  const etherscanApiKeys = get(keys)?.etherscan || {};
  return Object.keys(etherscanApiKeys).map((chain) => {
    const id = transformCase(chain);
    return ({
      id,
      name: get(getChainName(id)),
      evmChainName: id,
    });
  });
});

function setActiveTab(hash: string) {
  const evmChain = hash?.slice(1);
  const chains = get(supportedChains);
  const index = chains.findIndex(x => x.evmChainName === evmChain);
  nextTick(() => {
    if (index >= 0) {
      const serviceKey = get(serviceKeyCardRef);
      if (serviceKey) {
        serviceKey.setOpen(true);
      }
      set(tabIndex, index);
    }
  });
}

watch(route, ({ hash }) => {
  setActiveTab(hash);
});

onMounted(() => {
  setActiveTab(route.hash);
});
</script>

<template>
  <ServiceKeyCard
    ref="serviceKeyCardRef"
    data-cy="etherscan-api-keys"
    hide-action
    :title="t('external_services.etherscan.title')"
    :subtitle="t('external_services.etherscan.description')"
    image-src="./assets/images/services/etherscan.svg"
  >
    <RuiTabs
      v-model="tabIndex"
      color="primary"
    >
      <RuiTab
        v-for="chain in supportedChains"
        :key="chain.id"
        class="capitalize"
      >
        <div class="flex gap-4 items-center">
          <LocationIcon
            :item="chain.id"
            icon
          />
          {{ chain.name }}
        </div>
      </RuiTab>
    </RuiTabs>

    <RuiDivider class="mb-4" />

    <RuiTabItems v-model="tabIndex">
      <RuiTabItem
        v-for="chain in supportedChains"
        :key="chain.id"
      >
        <EtherscanApiKey
          :evm-chain="chain.evmChainName"
          :chain-name="chain.name"
        />
      </RuiTabItem>
    </RuiTabItems>
  </ServiceKeyCard>
</template>
