<template>
  <card>
    <template #title>
      {{ tc('external_services.title') }}
    </template>
    <template #subtitle>
      {{ tc('external_services.subtitle') }}
    </template>

    <api-key-box>
      <service-key
        v-model="etherscanKey"
        class="external-services__etherscan-key"
        :title="tc('external_services.etherscan.title')"
        :description="tc('external_services.etherscan.description')"
        :label="tc('external_services.etherscan.label')"
        :hint="tc('external_services.etherscan.hint')"
        :loading="loading"
        :tooltip="tc('external_services.etherscan.delete_tooltip')"
        @save="save('etherscan', $event)"
        @delete-key="deleteKey('etherscan')"
      />
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
        @delete-key="deleteKey('cryptocompare')"
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
        @delete-key="deleteKey('beaconchain')"
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
        @delete-key="deleteKey('covalent')"
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
        @delete-key="deleteKey('loopring')"
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
        @delete-key="deleteKey('opensea')"
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

    <confirm-dialog
      :title="tc('external_services.confirmation.title')"
      :message="tc('external_services.confirmation.message')"
      :display="!!serviceToDelete"
      @confirm="confirmDelete"
      @cancel="serviceToDelete = ''"
    />
  </card>
</template>

<script setup lang="ts">
import { computed, onMounted, Ref, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ApiKeyBox from '@/components/settings/api-keys/ApiKeyBox.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { default as i18nFn } from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import { useMainStore } from '@/store/main';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module } from '@/types/modules';
import {
  ExternalServiceKey,
  ExternalServiceKeys,
  ExternalServiceName
} from '@/types/user';
import { assert } from '@/utils/assertions';

const etherscanKey = ref('');
const cryptocompareKey = ref('');
const covalentKey = ref('');
const beaconchainKey = ref('');
const loopringKey = ref('');
const openseaKey = ref('');

const serviceToDelete: Ref<ExternalServiceName | ''> = ref('');

const loading = ref(false);

const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { setMessage } = useMainStore();
const { fetchLoopringBalances } = useBlockchainBalancesStore();

const { tc } = useI18n();

const isLoopringActive = computed(() => {
  return get(activeModules).includes(Module.LOOPRING);
});

const updateKeys = ({
  cryptocompare,
  covalent,
  etherscan,
  beaconchain,
  loopring,
  opensea
}: ExternalServiceKeys) => {
  set(cryptocompareKey, cryptocompare?.apiKey || '');
  set(covalentKey, covalent?.apiKey || '');
  set(etherscanKey, etherscan?.apiKey || '');
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
      title: i18nFn.t('external_services.set.success.title').toString(),
      description: i18nFn
        .t('external_services.set.success.message', {
          serviceName
        })
        .toString(),
      success: true
    });
    if (serviceName === 'loopring') {
      await fetchLoopringBalances(true);
    }
  } catch (e: any) {
    setMessage({
      title: i18nFn.t('external_services.set.error.title').toString(),
      description: i18nFn
        .t('external_services.set.error.message', {
          error: e.message
        })
        .toString(),
      success: false
    });
  }
  set(loading, false);
};

const deleteKey = (serviceName: ExternalServiceName) => {
  set(serviceToDelete, serviceName);
};

const confirmDelete = async () => {
  const exchangeName = get(serviceToDelete);
  assert(exchangeName);
  set(loading, true);
  try {
    updateKeys(await api.deleteExternalServices(exchangeName));
  } catch (e: any) {
    setMessage({
      title: i18nFn.t('external_services.delete_error.title').toString(),
      description: i18nFn
        .t('external_services.delete_error.description', {
          message: e.message
        })
        .toString(),
      success: false
    });
  }

  set(loading, false);
  set(serviceToDelete, '');
};

onMounted(async () => {
  set(loading, true);
  updateKeys(await api.queryExternalServices());
  set(loading, false);
});
</script>
