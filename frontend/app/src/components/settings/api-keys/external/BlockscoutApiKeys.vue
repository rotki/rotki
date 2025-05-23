<script setup lang="ts">
import LocationIcon from '@/components/history/LocationIcon.vue';
import BlockscoutApiKey from '@/components/settings/api-keys/external/BlockscoutApiKey.vue';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { transformCase } from '@rotki/common';

const { t } = useI18n({ useScope: 'global' });
const { keys } = useExternalApiKeys(t);
const tabIndex = ref<number>(0);
const route = useRoute();
const { getChainName } = useSupportedChains();

const supportedChains = computed(() => {
  const blockscoutApiKeys = get(keys)?.blockscout || {};
  return Object.keys(blockscoutApiKeys).map((chain) => {
    const id = transformCase(chain);
    return ({
      evmChainName: id,
      id,
      name: get(getChainName(id)),
    });
  });
});

function setActiveTab(hash: string) {
  const evmChain = hash?.slice(1);
  const chains = get(supportedChains);
  const index = chains.findIndex(x => x.evmChainName === evmChain);
  if (index >= 0) {
    set(tabIndex, index);
  }
}

watch([route, supportedChains], ([route, chains]) => {
  if (route && route.hash && chains.length > 0) {
    setActiveTab(route.hash);
  }
}, { immediate: true });
</script>

<template>
  <ServiceKeyCard
    hide-action
    :title="t('external_services.blockscout.title')"
    :subtitle="t('external_services.blockscout.description')"
    image-src="./assets/images/services/blockscout.svg"
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
        <BlockscoutApiKey
          :evm-chain="chain.evmChainName"
          :chain-name="chain.name"
        />
      </RuiTabItem>
    </RuiTabItems>
  </ServiceKeyCard>
</template>
