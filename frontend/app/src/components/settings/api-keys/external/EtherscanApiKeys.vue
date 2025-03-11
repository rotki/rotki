<script setup lang="ts">
import LocationIcon from '@/components/history/LocationIcon.vue';
import EtherscanApiKey from '@/components/settings/api-keys/external/EtherscanApiKey.vue';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Blockchain, transformCase } from '@rotki/common';

const { t } = useI18n();
const { keys } = useExternalApiKeys(t);
const tabIndex = ref<number>(0);
const route = useRoute();
const serviceKeyCardRef = ref<InstanceType<typeof ServiceKeyCard>>();
const unified = ref(false);

const { useUnifiedEtherscanApi } = storeToRefs(useGeneralSettingsStore());
const { getChainName } = useSupportedChains();

const supportedChains = computed(() => {
  const etherscanApiKeys = get(keys)?.etherscan || {};
  return Object.keys(etherscanApiKeys).map((chain) => {
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

watch([route, supportedChains], ([route, chains]) => {
  if (route && route.hash && chains.length > 0) {
    setActiveTab(route.hash);
  }
}, { immediate: true });

watchImmediate(useUnifiedEtherscanApi, (useUnifiedEtherscanApi) => {
  set(unified, useUnifiedEtherscanApi);
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
    <SettingsOption
      #default="{ updateImmediate }"
      setting="useUnifiedEtherscanApi"
    >
      <RuiCheckbox
        v-model="unified"
        color="primary"
        hide-details
        class="mb-3"
        :label="t('external_services.etherscan.unified')"
        @update:model-value="updateImmediate($event)"
      />
    </SettingsOption>

    <EtherscanApiKey
      v-if="unified"
      evm-chain="ethereum"
      :chain-name="Blockchain.ETH"
      unified
    />
    <div v-else>
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
    </div>
  </ServiceKeyCard>
</template>
