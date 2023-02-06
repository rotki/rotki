<script setup lang="ts">
import { type Ref } from 'vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ApiKeyBox from '@/components/settings/api-keys/ApiKeyBox.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { useExternalServicesApi } from '@/services/settings/external-services-api';
import { Module } from '@/types/modules';
import {
  type ExternalServiceKey,
  type ExternalServiceKeys,
  type ExternalServiceName
} from '@/types/user';
import { toCapitalCase, toSentenceCase } from '@/utils/text';

const evmEtherscanTabIndex: Ref<number> = ref(0);

interface EvmEtherscanTab {
  key: ExternalServiceName;
  value: string;
}

const evmEtherscanTabs: Record<string, EvmEtherscanTab> = reactive({
  ethereum: {
    key: 'etherscan',
    value: ''
  },
  optimism: {
    key: 'optimism_etherscan',
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

const { tc } = useI18n();
const api = useExternalServicesApi();

const isLoopringActive = computed(() => {
  return get(activeModules).includes(Module.LOOPRING);
});

const updateKeys = ({
  cryptocompare,
  covalent,
  etherscan,
  beaconchain,
  loopring,
  opensea,
  optimismEtherscan
}: ExternalServiceKeys) => {
  evmEtherscanTabs.ethereum.value = etherscan?.apiKey || '';
  evmEtherscanTabs.optimism.value = optimismEtherscan?.apiKey || '';
  set(cryptocompareKey, cryptocompare?.apiKey || '');
  set(covalentKey, covalent?.apiKey || '');
  set(beaconchainKey, beaconchain?.apiKey || '');
  set(loopringKey, loopring?.apiKey || '');
  set(openseaKey, opensea?.apiKey || '');
};

const save = async (serviceName: ExternalServiceName, key: string) => {
  const keys: ExternalServiceKey[] = [
    { name: serviceName, apiKey: key.trim() }
  ];

  try {
    set(loading, true);
    updateKeys(await api.setExternalServices(keys));
    setMessage({
      title: tc('external_services.set.success.title'),
      description: tc('external_services.set.success.message', 0, {
        serviceName: toCapitalCase(serviceName.split('_').join(' '))
      }),
      success: true
    });
    if (serviceName === 'loopring') {
      await fetchLoopringBalances(true);
    }
  } catch (e: any) {
    setMessage({
      title: tc('external_services.set.error.title'),
      description: tc('external_services.set.error.message', 0, {
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
      title: tc('external_services.confirmation.title'),
      message: tc('external_services.confirmation.message'),
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
      title: tc('external_services.delete_error.title'),
      description: tc('external_services.delete_error.description', 0, {
        message: e.message
      }),
      success: false
    });
  }

  set(loading, false);
};

onMounted(async () => {
  set(loading, true);
  updateKeys(await api.queryExternalServices());
  set(loading, false);
});
</script>

<template>
  <card>
    <template #title>
      {{ tc('external_services.title') }}
    </template>
    <template #subtitle>
      {{ tc('external_services.subtitle') }}
    </template>

    <api-key-box>
      <v-card flat>
        <v-card-title>
          {{ tc('external_services.etherscan.title') }}
        </v-card-title>
        <v-card-subtitle>
          {{ tc('external_services.etherscan.description') }}
        </v-card-subtitle>
      </v-card>
      <v-tabs v-model="evmEtherscanTabIndex">
        <v-tab v-for="(_, chain) in evmEtherscanTabs" :key="chain">
          <adaptive-wrapper>
            <evm-chain-icon :chain="chain" />
          </adaptive-wrapper>
          <div class="ml-2">{{ chain }}</div>
        </v-tab>
      </v-tabs>
      <v-divider />
      <v-tabs-items v-model="evmEtherscanTabIndex">
        <v-tab-item
          v-for="(tab, chain) in evmEtherscanTabs"
          :key="chain"
          class="pt-4"
        >
          <service-key
            v-model="tab.value"
            :class="`external-services__${chain}-etherscan-key`"
            :label="tc('external_services.etherscan.label')"
            :hint="tc('external_services.etherscan.hint')"
            :loading="loading"
            :tooltip="
              tc('external_services.etherscan.delete_tooltip', 0, {
                chain: toSentenceCase(chain)
              })
            "
            @save="save(tab.key, $event)"
            @delete-key="showConfirmation(tab.key)"
          />
        </v-tab-item>
      </v-tabs-items>
    </api-key-box>

    <api-key-box>
      <service-key
        v-model="cryptocompareKey"
        class="external-services__cryptocompare-key"
        :title="tc('external_services.cryptocompare.title')"
        :description="tc('external_services.cryptocompare.description')"
        :label="tc('external_services.cryptocompare.label')"
        :hint="tc('external_services.cryptocompare.hint')"
        :loading="loading"
        :tooltip="tc('external_services.cryptocompare.delete_tooltip')"
        @save="save('cryptocompare', $event)"
        @delete-key="showConfirmation('cryptocompare')"
      />
    </api-key-box>

    <api-key-box>
      <service-key
        v-model="beaconchainKey"
        class="external-services__beaconchain-key"
        :title="tc('external_services.beaconchain.title')"
        :description="tc('external_services.beaconchain.description')"
        :label="tc('external_services.beaconchain.label')"
        :hint="tc('external_services.beaconchain.hint')"
        :loading="loading"
        :tooltip="tc('external_services.beaconchain.delete_tooltip')"
        @save="save('beaconchain', $event)"
        @delete-key="showConfirmation('beaconchain')"
      />
    </api-key-box>

    <api-key-box>
      <service-key
        v-model="covalentKey"
        class="external-services__covalent-key"
        :title="tc('external_services.covalent.title')"
        :description="tc('external_services.covalent.description')"
        :label="tc('external_services.covalent.label')"
        :hint="tc('external_services.covalent.hint')"
        :loading="loading"
        :tooltip="tc('external_services.covalent.delete_tooltip')"
        @save="save('covalent', $event)"
        @delete-key="showConfirmation('covalent')"
      />
    </api-key-box>

    <api-key-box>
      <service-key
        v-model="loopringKey"
        class="external-services__loopring_key"
        :title="tc('external_services.loopring.title')"
        :description="tc('external_services.loopring.description')"
        :label="tc('external_services.loopring.label')"
        :hint="tc('external_services.loopring.hint')"
        :loading="loading"
        :tooltip="tc('external_services.loopring.delete_tooltip')"
        @save="save('loopring', $event)"
        @delete-key="showConfirmation('loopring')"
      />

      <v-alert
        v-if="loopringKey && !isLoopringActive"
        prominent
        type="warning"
        class="ma-2"
        outlined
      >
        <v-row align="center">
          <v-col class="grow">
            {{ tc('external_services.loopring.not_enabled') }}
          </v-col>
          <v-col class="shrink">
            <v-btn to="/settings/modules" color="primary">
              {{ tc('external_services.loopring.settings') }}
            </v-btn>
          </v-col>
        </v-row>
      </v-alert>
    </api-key-box>

    <api-key-box>
      <service-key
        v-model="openseaKey"
        class="external-services__opensea-key"
        :title="tc('external_services.opensea.title')"
        :description="tc('external_services.opensea.description')"
        :label="tc('external_services.opensea.label')"
        :hint="tc('external_services.opensea.hint')"
        :loading="loading"
        :tooltip="tc('external_services.opensea.delete_tooltip')"
        @save="save('opensea', $event)"
        @delete-key="showConfirmation('opensea')"
      >
        <i18n tag="div" path="external_services.opensea.link">
          <template #link>
            <external-link
              url="https://docs.opensea.io/reference/request-an-api-key"
            >
              {{ tc('external_services.opensea.here') }}
            </external-link>
          </template>
        </i18n>
      </service-key>
    </api-key-box>
  </card>
</template>
