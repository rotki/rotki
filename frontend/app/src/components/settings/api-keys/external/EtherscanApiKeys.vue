<script setup lang="ts">
import { type EvmChainInfo } from '@/types/api/chains';

const { txEvmChains } = useSupportedChains();

const tabIndex: Ref<number> = ref(0);

const { t } = useI18n();
const route = useRoute();

const setActiveTab = (hash: string) => {
  const evmChain = hash?.slice(1);
  const chains: EvmChainInfo[] = get(txEvmChains);
  const index = chains.findIndex(x => x.evmChainName === evmChain);
  if (index >= 0) {
    set(tabIndex, index);
  }
};

watch(route, ({ hash }) => {
  setActiveTab(hash);
});

onMounted(async () => {
  setActiveTab(route.hash);
});
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('external_services.etherscan.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.etherscan.description') }}
    </template>

    <RuiTabs v-model="tabIndex" color="primary">
      <RuiTab v-for="chain in txEvmChains" :key="chain.id" class="capitalize">
        <div class="flex gap-4 items-center">
          <LocationIcon :item="chain.id" icon />
          {{ chain.name }}
        </div>
      </RuiTab>
    </RuiTabs>

    <RuiDivider class="mb-4" />

    <RuiTabItems v-model="tabIndex">
      <RuiTabItem v-for="chain in txEvmChains" :key="chain.id">
        <EtherscanApiKey
          :evm-chain="chain.evmChainName"
          :chain-name="chain.name"
        />
      </RuiTabItem>
    </RuiTabItems>
  </RuiCard>
</template>
