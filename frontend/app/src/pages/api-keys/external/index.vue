<script setup lang="ts">
import type { Component, ComputedRef } from 'vue';
import { getTextToken } from '@rotki/common';
import { type MessageKey, msg } from '@/message-key';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';
import { EXTERNAL_API_KEY_SERVICES, type ExternalApiKeyService } from '@/modules/settings/api-keys/external/external-api-key-services';
import ExternalApiKeyCard from '@/modules/settings/api-keys/external/ExternalApiKeyCard.vue';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

/** A plain key card built from the services table, or an integration with its own component. */
type ServiceEntry = { readonly name: string; readonly setUp: ComputedRef<boolean> } & (
  | { readonly service: ExternalApiKeyService }
  | { readonly component: Component }
);

interface ServiceGroup {
  readonly key: string;
  readonly title: MessageKey;
  readonly entries: ServiceEntry[];
}

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.api_keys_sub.external_services'), icon: 'lu-blocks', parent: '/api-keys/', order: 30, drawer: 'api-keys-external-services' },
  },
});

const { t } = useI18n({ useScope: 'global' });

const search = ref<string>('');
const setUpOnly = ref<boolean>(false);
const { load, useApiKey } = useExternalApiKeys();
const { authenticated: moneriumConnected } = useMoneriumOAuth();

function card(service: ExternalApiKeyService): ServiceEntry {
  const key = useApiKey(service.name);
  return { name: service.name, service, setUp: computed<boolean>(() => !!get(key)) };
}

const gnosisPayKey = useApiKey('gnosis_pay');

/** The services by what rotki uses them for, so a key is found by its purpose rather than its name. */
const groups: ServiceGroup[] = [{
  entries: [
    card(EXTERNAL_API_KEY_SERVICES.etherscan),
    card(EXTERNAL_API_KEY_SERVICES.blockscout),
    card(EXTERNAL_API_KEY_SERVICES.helius),
    card(EXTERNAL_API_KEY_SERVICES.thegraph),
  ],
  key: 'blockchain',
  title: msg.$t('external_services.groups.blockchain'),
}, {
  entries: [
    card(EXTERNAL_API_KEY_SERVICES.cryptocompare),
    card(EXTERNAL_API_KEY_SERVICES.defillama),
    card(EXTERNAL_API_KEY_SERVICES.coingecko),
    card(EXTERNAL_API_KEY_SERVICES.alchemy),
    card(EXTERNAL_API_KEY_SERVICES.moralis),
    card(EXTERNAL_API_KEY_SERVICES.birdeye),
  ],
  key: 'prices',
  title: msg.$t('external_services.groups.prices'),
}, {
  entries: [
    card(EXTERNAL_API_KEY_SERVICES.beaconchain),
    card(EXTERNAL_API_KEY_SERVICES.opensea),
  ],
  key: 'staking',
  title: msg.$t('external_services.groups.staking'),
}, {
  entries: [{
    component: defineAsyncComponent(() => import('@/modules/integrations/monerium/MoneriumAuth.vue')),
    name: 'monerium',
    setUp: computed<boolean>(() => get(moneriumConnected)),
  }, {
    component: defineAsyncComponent(() => import('@/modules/integrations/gnosis-pay/components/GnosisPayAuth.vue')),
    name: 'gnosispay',
    setUp: computed<boolean>(() => !!get(gnosisPayKey)),
  }],
  key: 'integrations',
  title: msg.$t('external_services.groups.integrations'),
}];

const allEntries = groups.flatMap(group => group.entries);

const setUpCount = computed<number>(() => allEntries.filter(entry => get(entry.setUp)).length);

/** The groups with what the search and the set-up switch leave in them; an emptied group is dropped. */
const visibleGroups = computed<ServiceGroup[]>(() => {
  const keyword = getTextToken(get(search));
  const onlySetUp = get(setUpOnly);
  return groups
    .map(group => ({
      ...group,
      entries: group.entries.filter(entry => (!keyword || getTextToken(entry.name).includes(keyword))
        && (!onlySetUp || get(entry.setUp))),
    }))
    .filter(group => group.entries.length > 0);
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
    <div class="flex flex-col gap-6">
      <div class="flex flex-wrap items-center gap-3">
        <RuiTextField
          v-model="search"
          color="primary"
          clearable
          dense
          hide-details
          class="w-full sm:w-80"
          :placeholder="t('external_services.search')"
          prepend-icon="lu-search"
          data-testid="external-services-search"
        />
        <HintMenuIcon>
          {{ t('external_services.subtitle') }}
        </HintMenuIcon>
        <div class="grow" />
        <RuiChip
          size="sm"
          variant="tonal"
          :color="setUpCount > 0 ? 'success' : 'grey'"
          data-testid="external-services-count"
        >
          {{ t('external_services.set_up_count', { count: setUpCount, total: allEntries.length }) }}
        </RuiChip>
        <RuiSwitch
          v-model="setUpOnly"
          color="primary"
          size="sm"
          hide-details
          :label="t('external_services.set_up_only')"
        />
      </div>

      <section
        v-for="group in visibleGroups"
        :key="group.key"
        class="flex flex-col gap-3"
        :data-testid="`external-services-group-${group.key}`"
      >
        <h2 class="m-0 text-sm font-semibold uppercase tracking-wide text-rui-text-secondary">
          {{ t(group.title) }}
        </h2>
        <div class="grid sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-4">
          <template
            v-for="entry in group.entries"
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
        </div>
      </section>

      <div
        v-if="visibleGroups.length === 0"
        class="py-12 text-center text-sm text-rui-text-secondary"
      >
        {{ t('external_services.no_services_found') }}
      </div>
    </div>
  </TablePageLayout>
</template>
