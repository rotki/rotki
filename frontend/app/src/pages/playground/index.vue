<script setup lang="ts">
import { SUPPORTED_MODULES } from '@/types/modules';

const { supportedChains } = useSupportedChains();
const { allLocations, allExchanges } = storeToRefs(useLocationStore());

const integrationData = computed(() => {
  const blockchains = get(supportedChains)
    .filter(item => item.name !== 'Ethereum Staking')
    .map(item => ({
      label: toSentenceCase(item.name),
      image: `https://raw.githubusercontent.com/rotki/rotki/develop/frontend/app/public/assets/images/protocols/${item.image}`,
    }));

  const exchanges = get(allExchanges).map((item) => {
    const data = get(allLocations)[item];

    return {
      label: data.label || toSentenceCase(item),
      image: `https://raw.githubusercontent.com/rotki/rotki/develop/frontend/app/public/assets/images/protocols/${data.image}`,
    };
  });

  const protocols = SUPPORTED_MODULES.map(item => ({
    label: item.name,
    image: `https://raw.githubusercontent.com/rotki/rotki/develop/frontend/app/public${item.icon.slice(1)}`,
  }));

  const data = {
    blockchains,
    exchanges,
    protocols,
  };

  return JSON.stringify(data, null, 2);
});

const { copy: copyGeneratedIntegrationData } = useClipboard({ source: integrationData });

const copyText = 'Copy Integration JSON Data';
</script>

<template>
  <div class="container pt-8">
    <!-- insert components to be tested here -->
    <RuiButton @click="copyGeneratedIntegrationData()">
      {{ copyText }}
    </RuiButton>
  </div>
</template>
