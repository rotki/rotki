<script setup lang="ts">
import { type Ref } from 'vue';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import {
  TRADE_LOCATION_ARBITRUM_ONE,
  TRADE_LOCATION_BASE,
  TRADE_LOCATION_ETHEREUM,
  TRADE_LOCATION_OPTIMISM,
  TRADE_LOCATION_POLYGON_POS
} from '@/data/defaults';
import { Module } from '@/types/modules';
import { toSentenceCase } from '@/utils/text';
import type {
  ExternalServiceKey,
  ExternalServiceKeys,
  ExternalServiceName
} from '@/types/user';

const evmEtherscanTabIndex: Ref<number> = ref(0);

interface EvmEtherscanTab {
  key: ExternalServiceName;
  value: string;
}

const evmEtherscanTabs = reactive<Record<string, EvmEtherscanTab>>({
  [TRADE_LOCATION_ETHEREUM]: {
    key: 'etherscan',
    value: ''
  },
  [TRADE_LOCATION_OPTIMISM]: {
    key: 'optimism_etherscan',
    value: ''
  },
  [TRADE_LOCATION_POLYGON_POS]: {
    key: 'polygon_pos_etherscan',
    value: ''
  },
  [TRADE_LOCATION_ARBITRUM_ONE]: {
    key: 'arbitrum_one_etherscan',
    value: ''
  },
  [TRADE_LOCATION_BASE]: {
    key: 'base_etherscan',
    value: ''
  }
});

const cryptocompareKey = ref('');
const covalentKey = ref('');
const beaconchainKey = ref('');
const loopringKey = ref('');
const openseaKey = ref('');

const loading = ref(false);

const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { setMessage } = useMessageStore();
const { fetchLoopringBalances } = useEthBalancesStore();
const { remove: removeNotification, prioritized } = useNotificationsStore();
const { getChainName } = useSupportedChains();

const { t } = useI18n();
const route = useRoute();
const api = useExternalServicesApi();

const isLoopringActive = computed(() =>
  get(activeModules).includes(Module.LOOPRING)
);

const updateKeys = ({
  cryptocompare,
  covalent,
  etherscan,
  beaconchain,
  loopring,
  opensea,
  optimismEtherscan,
  polygonPosEtherscan,
  arbitrumOneEtherscan,
  baseEtherscan
}: ExternalServiceKeys) => {
  evmEtherscanTabs[TRADE_LOCATION_ETHEREUM].value = etherscan?.apiKey || '';
  evmEtherscanTabs[TRADE_LOCATION_OPTIMISM].value =
    optimismEtherscan?.apiKey || '';
  evmEtherscanTabs[TRADE_LOCATION_POLYGON_POS].value =
    polygonPosEtherscan?.apiKey || '';
  evmEtherscanTabs[TRADE_LOCATION_ARBITRUM_ONE].value =
    arbitrumOneEtherscan?.apiKey || '';
  evmEtherscanTabs[TRADE_LOCATION_BASE].value = baseEtherscan?.apiKey || '';
  set(cryptocompareKey, cryptocompare?.apiKey || '');
  set(covalentKey, covalent?.apiKey || '');
  set(beaconchainKey, beaconchain?.apiKey || '');
  set(loopringKey, loopring?.apiKey || '');
  set(openseaKey, opensea?.apiKey || '');
};

/**
 * After an api key is added, remove the etherscan notification for that location
 * @param {string} location
 */
const removeEtherscanNotification = (location: string) => {
  // using prioritized list here, because the actionable notifications are always on top (index 0|1)
  // so it is faster to find
  const notification = prioritized.find(
    data => data.i18nParam?.props?.key === location
  );

  if (!notification) {
    return;
  }

  removeNotification(notification.id);
};

const save = async (serviceName: ExternalServiceName, key: string) => {
  const keys: ExternalServiceKey[] = [
    { name: serviceName, apiKey: key.trim() }
  ];

  try {
    set(loading, true);
    updateKeys(await api.setExternalServices(keys));
    setMessage({
      title: t('external_services.set.success.title'),
      description: t('external_services.set.success.message', {
        serviceName: toCapitalCase(serviceName.split('_').join(' '))
      }),
      success: true
    });
    if (serviceName === 'loopring') {
      await fetchLoopringBalances(true);
    } else if (serviceName === 'etherscan') {
      removeEtherscanNotification(TRADE_LOCATION_ETHEREUM);
    } else if (serviceName === 'optimism_etherscan') {
      removeEtherscanNotification(TRADE_LOCATION_OPTIMISM);
    } else if (serviceName === 'polygon_pos_etherscan') {
      removeEtherscanNotification(TRADE_LOCATION_POLYGON_POS);
    } else if (serviceName === 'arbitrum_one_etherscan') {
      removeEtherscanNotification(TRADE_LOCATION_ARBITRUM_ONE);
    } else if (serviceName === 'base_etherscan') {
      removeEtherscanNotification(TRADE_LOCATION_BASE);
    }
  } catch (e: any) {
    setMessage({
      title: t('external_services.set.error.title'),
      description: t('external_services.set.error.message', {
        error: e.message
      }),
      success: false
    });
  }
  set(loading, false);
};

const { show } = useConfirmStore();

const showConfirmation = (service: ExternalServiceName) => {
  show(
    {
      title: t('external_services.confirmation.title'),
      message: t('external_services.confirmation.message'),
      type: 'info'
    },
    async () => await confirm(service)
  );
};

const confirm = async (service: ExternalServiceName) => {
  set(loading, true);
  try {
    updateKeys(await api.deleteExternalServices(service));
  } catch (e: any) {
    setMessage({
      title: t('external_services.delete_error.title'),
      description: t('external_services.delete_error.description', {
        message: e.message
      }),
      success: false
    });
  }

  set(loading, false);
};

const getName = (chain: string) => get(getChainName(chain as Blockchain));

const setActiveTab = (hash: string) => {
  const id = hash?.slice(1);
  if (id && id in evmEtherscanTabs) {
    set(evmEtherscanTabIndex, Object.keys(evmEtherscanTabs).indexOf(id));
  }
};

watch(route, ({ hash }) => {
  setActiveTab(hash);
});

onMounted(async () => {
  setActiveTab(route.hash);
  set(loading, true);
  updateKeys(await api.queryExternalServices());
  set(loading, false);
});
</script>

<template>
  <Card>
    <template #title>
      {{ t('external_services.title') }}
    </template>
    <template #subtitle>
      {{ t('external_services.subtitle') }}
    </template>

    <ApiKeyBox>
      <VCard flat :outlined="false">
        <VCardTitle>
          {{ t('external_services.etherscan.title') }}
        </VCardTitle>
        <VCardSubtitle>
          {{ t('external_services.etherscan.description') }}
        </VCardSubtitle>
      </VCard>
      <VTabs v-model="evmEtherscanTabIndex">
        <VTab v-for="(_, chain) in evmEtherscanTabs" :key="chain">
          <LocationIcon :item="chain" icon />
          <div class="ml-2">{{ getName(chain) }}</div>
        </VTab>
      </VTabs>
      <VDivider />
      <VTabsItems v-model="evmEtherscanTabIndex">
        <VTabItem
          v-for="(tab, chain) in evmEtherscanTabs"
          :key="chain"
          class="pt-4"
        >
          <ServiceKey
            v-model="tab.value"
            :class="`external-services__${chain}-etherscan-key`"
            :label="t('external_services.etherscan.label')"
            :hint="
              t('external_services.etherscan.hint', {
                chain: getName(chain)
              })
            "
            :loading="loading"
            :tooltip="
              t('external_services.etherscan.delete_tooltip', {
                chain: toSentenceCase(chain)
              })
            "
            @save="save(tab.key, $event)"
            @delete-key="showConfirmation(tab.key)"
          />
        </VTabItem>
      </VTabsItems>
    </ApiKeyBox>

    <ApiKeyBox id="ext-service-key-cryptocompare">
      <ServiceKey
        v-model="cryptocompareKey"
        class="external-services__cryptocompare-key"
        :title="t('external_services.cryptocompare.title')"
        :description="t('external_services.cryptocompare.description')"
        :label="t('external_services.cryptocompare.label')"
        :hint="t('external_services.cryptocompare.hint')"
        :loading="loading"
        :tooltip="t('external_services.cryptocompare.delete_tooltip')"
        @save="save('cryptocompare', $event)"
        @delete-key="showConfirmation('cryptocompare')"
      />
    </ApiKeyBox>

    <ApiKeyBox id="ext-service-key-beaconchain">
      <ServiceKey
        v-model="beaconchainKey"
        class="external-services__beaconchain-key"
        :title="t('external_services.beaconchain.title')"
        :description="t('external_services.beaconchain.description')"
        :label="t('external_services.beaconchain.label')"
        :hint="t('external_services.beaconchain.hint')"
        :loading="loading"
        :tooltip="t('external_services.beaconchain.delete_tooltip')"
        @save="save('beaconchain', $event)"
        @delete-key="showConfirmation('beaconchain')"
      />
    </ApiKeyBox>

    <ApiKeyBox id="ext-service-key-covalent">
      <ServiceKey
        v-model="covalentKey"
        class="external-services__covalent-key"
        :title="t('external_services.covalent.title')"
        :description="t('external_services.covalent.description')"
        :label="t('external_services.covalent.label')"
        :hint="t('external_services.covalent.hint')"
        :loading="loading"
        :tooltip="t('external_services.covalent.delete_tooltip')"
        @save="save('covalent', $event)"
        @delete-key="showConfirmation('covalent')"
      />
    </ApiKeyBox>

    <ApiKeyBox id="ext-service-key-loopring">
      <ServiceKey
        v-model="loopringKey"
        class="external-services__loopring_key"
        :title="t('external_services.loopring.title')"
        :description="t('external_services.loopring.description')"
        :label="t('external_services.loopring.label')"
        :hint="t('external_services.loopring.hint')"
        :loading="loading"
        :tooltip="t('external_services.loopring.delete_tooltip')"
        @save="save('loopring', $event)"
        @delete-key="showConfirmation('loopring')"
      />

      <VAlert
        v-if="loopringKey && !isLoopringActive"
        prominent
        type="warning"
        class="ma-2"
        outlined
      >
        <VRow align="center">
          <VCol class="grow">
            {{ t('external_services.loopring.not_enabled') }}
          </VCol>
          <VCol class="shrink">
            <VBtn to="/settings/modules" color="primary">
              {{ t('external_services.loopring.settings') }}
            </VBtn>
          </VCol>
        </VRow>
      </VAlert>
    </ApiKeyBox>

    <ApiKeyBox id="ext-service-key-opensea">
      <ServiceKey
        v-model="openseaKey"
        class="external-services__opensea-key"
        :title="t('external_services.opensea.title')"
        :description="t('external_services.opensea.description')"
        :label="t('external_services.opensea.label')"
        :hint="t('external_services.opensea.hint')"
        :loading="loading"
        :tooltip="t('external_services.opensea.delete_tooltip')"
        @save="save('opensea', $event)"
        @delete-key="showConfirmation('opensea')"
      >
        <i18n tag="div" path="external_services.opensea.link">
          <template #link>
            <ExternalLink
              url="https://docs.opensea.io/reference/api-keys#how-do-i-get-an-api-key"
            >
              {{ t('common.here') }}
            </ExternalLink>
          </template>
        </i18n>
      </ServiceKey>
    </ApiKeyBox>
  </Card>
</template>
