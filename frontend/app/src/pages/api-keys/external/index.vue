<script setup lang="ts">
import type { Component } from 'vue';
import { getTextToken } from '@rotki/common';
import { msg } from '@/message-key';
import { EXTERNAL_API_KEY_SERVICES, type ExternalApiKeyService } from '@/modules/settings/api-keys/external/external-api-key-services';
import ExternalApiKeyCard from '@/modules/settings/api-keys/external/ExternalApiKeyCard.vue';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

/** A plain key card built from the services table, or an integration with its own component. */
type ServiceEntry =
  | { readonly name: string; readonly service: ExternalApiKeyService }
  | { readonly name: string; readonly component: Component };

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.api_keys_sub.external_services'), icon: 'lu-blocks', parent: '/api-keys/', order: 30, drawer: 'api-keys-external-services' },
  },
});

const { t } = useI18n({ useScope: 'global' });

const search = ref<string>('');
const { load } = useExternalApiKeys();

function card(service: ExternalApiKeyService): ServiceEntry {
  return { name: service.name, service };
}

const services: ServiceEntry[] = [
  card(EXTERNAL_API_KEY_SERVICES.etherscan),
  card(EXTERNAL_API_KEY_SERVICES.blockscout),
  card(EXTERNAL_API_KEY_SERVICES.helius),
  card(EXTERNAL_API_KEY_SERVICES.cryptocompare),
  card(EXTERNAL_API_KEY_SERVICES.beaconchain),
  card(EXTERNAL_API_KEY_SERVICES.opensea),
  {
    component: defineAsyncComponent(() => import('@/modules/integrations/monerium/MoneriumAuth.vue')),
    name: 'monerium',
  },
  card(EXTERNAL_API_KEY_SERVICES.thegraph),
  {
    component: defineAsyncComponent(() => import('@/modules/integrations/gnosis-pay/components/GnosisPayAuth.vue')),
    name: 'gnosispay',
  },
  card(EXTERNAL_API_KEY_SERVICES.defillama),
  card(EXTERNAL_API_KEY_SERVICES.coingecko),
  card(EXTERNAL_API_KEY_SERVICES.alchemy),
  card(EXTERNAL_API_KEY_SERVICES.moralis),
  card(EXTERNAL_API_KEY_SERVICES.birdeye),
];

const filteredServices = computed<ServiceEntry[]>(() => {
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
    data-testid="external-keys"
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
        <template
          v-for="entry in filteredServices"
          :key="entry.name"
        >
          <ExternalApiKeyCard
            v-if="'service' in entry"
            :service="entry.service"
          />
          <Component
            :is="entry.component"
            v-else
          />
        </template>
      </template>
      <template v-else>
        <div class="p-4">
          {{ t('external_services.no_services_found') }}
        </div>
      </template>
    </div>
  </TablePageLayout>
</template>
