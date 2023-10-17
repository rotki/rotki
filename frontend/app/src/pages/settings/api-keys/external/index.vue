<script setup lang="ts">
import { type Ref } from 'vue';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import {
  TRADE_LOCATION_ARBITRUM_ONE,
  TRADE_LOCATION_BASE,
  TRADE_LOCATION_ETHEREUM,
  TRADE_LOCATION_GNOSIS,
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
  // TODO: remove the string modification when https://github.com/rotki/rotki/issues/6725 is resolved
  [toSnakeCase(TRADE_LOCATION_POLYGON_POS)]: {
    key: 'polygon_pos_etherscan',
    value: ''
  },
  // TODO: remove the string modification when https://github.com/rotki/rotki/issues/6725 is resolved
  [toSnakeCase(TRADE_LOCATION_ARBITRUM_ONE)]: {
    key: 'arbitrum_one_etherscan',
    value: ''
  },
  [TRADE_LOCATION_BASE]: {
    key: 'base_etherscan',
    value: ''
  },
  [TRADE_LOCATION_GNOSIS]: {
    key: 'gnosis_etherscan',
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
  baseEtherscan,
  gnosisEtherscan
}: ExternalServiceKeys) => {
  evmEtherscanTabs[TRADE_LOCATION_ETHEREUM].value = etherscan?.apiKey || '';
  evmEtherscanTabs[TRADE_LOCATION_OPTIMISM].value =
    optimismEtherscan?.apiKey || '';
  // TODO: remove the string modification when https://github.com/rotki/rotki/issues/6725 is resolved
  evmEtherscanTabs[toSnakeCase(TRADE_LOCATION_POLYGON_POS)].value =
    polygonPosEtherscan?.apiKey || '';
  // TODO: remove the string modification when https://github.com/rotki/rotki/issues/6725 is resolved
  evmEtherscanTabs[toSnakeCase(TRADE_LOCATION_ARBITRUM_ONE)].value =
    arbitrumOneEtherscan?.apiKey || '';
  evmEtherscanTabs[TRADE_LOCATION_BASE].value = baseEtherscan?.apiKey || '';
  evmEtherscanTabs[TRADE_LOCATION_GNOSIS].value = gnosisEtherscan?.apiKey || '';
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

const save = async ({
  name,
  apiKey
}: {
  name: ExternalServiceName;
  apiKey: string;
}) => {
  const keys: ExternalServiceKey[] = [{ name, apiKey: apiKey.trim() }];

  try {
    set(loading, true);
    updateKeys(await api.setExternalServices(keys));
    setMessage({
      title: t('external_services.set.success.title'),
      description: t('external_services.set.success.message', {
        serviceName: toCapitalCase(name.split('_').join(' '))
      }),
      success: true
    });
    if (name === 'loopring') {
      await fetchLoopringBalances(true);
    } else if (name === 'etherscan') {
      removeEtherscanNotification(TRADE_LOCATION_ETHEREUM);
    } else if (name === 'optimism_etherscan') {
      removeEtherscanNotification(TRADE_LOCATION_OPTIMISM);
    } else if (name === 'polygon_pos_etherscan') {
      // TODO: remove the string modification when https://github.com/rotki/rotki/issues/6725 is resolved
      removeEtherscanNotification(toSnakeCase(TRADE_LOCATION_POLYGON_POS));
    } else if (name === 'arbitrum_one_etherscan') {
      // TODO: remove the string modification when https://github.com/rotki/rotki/issues/6725 is resolved
      removeEtherscanNotification(toSnakeCase(TRADE_LOCATION_ARBITRUM_ONE));
    } else if (name === 'base_etherscan') {
      removeEtherscanNotification(TRADE_LOCATION_BASE);
    } else if (name === 'gnosis_etherscan') {
      removeEtherscanNotification(TRADE_LOCATION_GNOSIS);
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

const navigateToModules = () => useRouter().push('/settings/modules');

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
  <TablePageLayout
    data-cy="external-keys"
    :title="[
      t('navigation_menu.api_keys'),
      t('navigation_menu.api_keys_sub.external_services')
    ]"
  >
    <template #buttons>
      <HintMenuIcon max-width="25rem">
        {{ t('external_services.subtitle') }}
      </HintMenuIcon>
    </template>

    <RuiCard>
      <template #header>
        {{ t('external_services.etherscan.title') }}
      </template>
      <template #subheader>
        {{ t('external_services.etherscan.description') }}
      </template>

      <RuiTabs
        v-model="evmEtherscanTabIndex"
        color="primary"
        class="border-b mb-4"
      >
        <RuiTab
          v-for="(_, chain) in evmEtherscanTabs"
          :key="chain"
          class="capitalize"
        >
          <div class="flex gap-4 items-center">
            <LocationIcon :item="chain" icon />
            {{ getName(chain) }}
          </div>
        </RuiTab>
      </RuiTabs>

      <RuiTabItems v-model="evmEtherscanTabIndex">
        <RuiTabItem v-for="(tab, chain) in evmEtherscanTabs" :key="chain">
          <ServiceKey
            :api-key="tab.value"
            :name="tab.key"
            :data-cy="tab.key"
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
            @save="save($event)"
            @delete-key="showConfirmation($event)"
          />
        </RuiTabItem>
      </RuiTabItems>
    </RuiCard>

    <RuiCard>
      <template #header>
        {{ t('external_services.cryptocompare.title') }}
      </template>
      <template #subheader>
        {{ t('external_services.cryptocompare.description') }}
      </template>

      <ServiceKey
        :api-key="cryptocompareKey"
        name="cryptocompare"
        data-cy="cryptocompare"
        :label="t('external_services.cryptocompare.label')"
        :hint="t('external_services.cryptocompare.hint')"
        :loading="loading"
        :tooltip="t('external_services.cryptocompare.delete_tooltip')"
        @save="save($event)"
        @delete-key="showConfirmation($event)"
      />
    </RuiCard>

    <RuiCard>
      <template #header>
        {{ t('external_services.beaconchain.title') }}
      </template>
      <template #subheader>
        {{ t('external_services.beaconchain.description') }}
      </template>

      <ServiceKey
        :api-key="beaconchainKey"
        name="beaconchain"
        data-cy="beaconchain"
        :label="t('external_services.beaconchain.label')"
        :hint="t('external_services.beaconchain.hint')"
        :loading="loading"
        :tooltip="t('external_services.beaconchain.delete_tooltip')"
        @save="save($event)"
        @delete-key="showConfirmation($event)"
      />
    </RuiCard>

    <RuiCard>
      <template #header>
        {{ t('external_services.covalent.title') }}
      </template>
      <template #subheader>
        {{ t('external_services.covalent.description') }}
      </template>

      <ServiceKey
        :api-key="covalentKey"
        name="covalent"
        data-cy="covalent"
        :label="t('external_services.covalent.label')"
        :hint="t('external_services.covalent.hint')"
        :loading="loading"
        :tooltip="t('external_services.covalent.delete_tooltip')"
        @save="save($event)"
        @delete-key="showConfirmation($event)"
      />
    </RuiCard>

    <RuiCard>
      <template #header>
        {{ t('external_services.loopring.title') }}
      </template>
      <template #subheader>
        {{ t('external_services.loopring.description') }}
      </template>

      <ServiceKey
        :api-key="loopringKey"
        name="loopring"
        data-cy="loopring"
        :label="t('external_services.loopring.label')"
        :hint="t('external_services.loopring.hint')"
        :loading="loading"
        :tooltip="t('external_services.loopring.delete_tooltip')"
        @save="save($event)"
        @delete-key="showConfirmation($event)"
      >
        <RuiAlert v-if="loopringKey && !isLoopringActive" type="warning">
          <div class="flex gap-4 items-center">
            <div class="grow">
              {{ t('external_services.loopring.not_enabled') }}
            </div>
            <RuiButton size="sm" color="primary" @click="navigateToModules()">
              {{ t('external_services.loopring.settings') }}
            </RuiButton>
          </div>
        </RuiAlert>
      </ServiceKey>
    </RuiCard>

    <RuiCard>
      <template #header>
        {{ t('external_services.opensea.title') }}
      </template>
      <template #subheader>
        {{ t('external_services.opensea.description') }}
      </template>

      <ServiceKey
        :api-key="openseaKey"
        name="opensea"
        data-cy="opensea"
        :label="t('external_services.opensea.label')"
        :hint="t('external_services.opensea.hint')"
        :loading="loading"
        :tooltip="t('external_services.opensea.delete_tooltip')"
        @save="save($event)"
        @delete-key="showConfirmation($event)"
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
    </RuiCard>
  </TablePageLayout>
</template>
