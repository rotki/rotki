<script setup lang="ts">
import { Routes } from '@/router/routes';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';

function reset() {
  sessionStorage.removeItem('vuex');
  window.location.reload();
}

const resetState = 'Reset State';

const { supportedChains } = useSupportedChains();
const { allLocations, allExchanges } = storeToRefs(useLocationStore());
const { getCounterpartyData, counterparties } = useHistoryEventCounterpartyMappings();

const imageUrl = 'https://raw.githubusercontent.com/rotki/rotki/develop/frontend/app/public/assets/images/protocols/';

const integrationData = computed(() => {
  const blockchains = get(supportedChains)
    .filter(item => item.name !== 'Ethereum Staking')
    .map(item => ({
      label: toSentenceCase(item.name),
      image: `${imageUrl}${item.image}`,
    }));

  const exchanges = get(allExchanges).map((item) => {
    const data = get(allLocations)[item];

    return {
      label: data.label || toSentenceCase(item),
      image: `${imageUrl}${data.image}`,
    };
  });

  const protocols = get(counterparties)
    .filter(item => item !== 'gas' && !/v\d+$/.test(item)) // remove gas, and anything that has version number
    .filter(uniqueStrings)
    .map((item) => {
      const data = get(getCounterpartyData(item));
      return {
        label: toHumanReadable(data.label, 'sentence'),
        image: `${imageUrl}${data.image}`,
      };
    });

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
  <div
    id="rotki"
    class="w-full h-full"
  >
    <nav class="border-default bg-white dark:bg-black border-b flex gap-4 items-center fixed w-full p-2 top-0">
      <RouterLink :to="Routes.DASHBOARD">
        <RuiButton
          variant="text"
          icon
        >
          <RuiIcon name="home-3-line" />
        </RuiButton>
      </RouterLink>
      <div class="grow" />
      <RuiButton
        color="primary"
        @click="copyGeneratedIntegrationData()"
      >
        {{ copyText }}
      </RuiButton>
      <RuiButton
        variant="outlined"
        color="warning"
        @click="reset()"
      >
        <template #prepend>
          <RuiIcon name="restart-line" />
        </template>
        {{ resetState }}
      </RuiButton>
    </nav>
    <div class="w-full h-full">
      <RouterView />
    </div>
  </div>
</template>
