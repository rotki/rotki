<template>
  <setting-category>
    <template #title>
      {{ tc('data_management.title') }}
    </template>
    <template #subtitle>
      {{ tc('data_management.subtitle') }}
    </template>

    <v-form ref="form">
      <v-row>
        <v-col>
          <purge-selector
            v-model="source"
            :status="status"
            :pending="pending"
            @purge="showConfirmation($event)"
          />
        </v-col>
      </v-row>
    </v-form>
  </setting-category>
</template>
<script setup lang="ts">
import PurgeSelector from '@/components/settings/data-security/PurgeSelector.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import { api } from '@/services/rotkehlchen-api';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS
} from '@/services/session/consts';
import { type Purgeable } from '@/services/session/types';
import { useConfirmStore } from '@/store/confirm';
import { useSessionPurgeStore } from '@/store/session/purge';
import { SUPPORTED_EXCHANGES, type SupportedExchange } from '@/types/exchanges';
import { type BaseMessage } from '@/types/messages';
import { Module } from '@/types/modules';
import { type PurgeParams } from '@/types/purge';

const source = ref<Purgeable>(ALL_TRANSACTIONS);
const status = ref<BaseMessage | null>(null);
const confirm = ref<boolean>(false);
const pending = ref<boolean>(false);

const { purgeCache } = useSessionPurgeStore();

const { tc } = useI18n();
const { show } = useConfirmStore();

const showConfirmation = (source: PurgeParams) => {
  show(
    {
      title: tc('data_management.confirm.title'),
      message: tc('data_management.confirm.message', 0, { source: source.text })
    },
    async () => purge(source)
  );
  set(confirm, true);
};

const purgeSource = async (source: Purgeable) => {
  if (source === ALL_TRANSACTIONS) {
    await api.balances.deleteEthereumTransactions();
  } else if (source === ALL_MODULES) {
    await api.balances.deleteModuleData();
  } else if (source === ALL_CENTRALIZED_EXCHANGES) {
    await api.balances.deleteExchangeData();
  } else if (source === ALL_DECENTRALIZED_EXCHANGES) {
    await Promise.all([
      api.balances.deleteModuleData(Module.UNISWAP),
      api.balances.deleteModuleData(Module.BALANCER)
    ]);
  } else if (
    SUPPORTED_EXCHANGES.includes(source as any) ||
    EXTERNAL_EXCHANGES.includes(source as any)
  ) {
    await api.balances.deleteExchangeData(source as SupportedExchange);
  } else if (Object.values(Module).includes(source as any)) {
    await api.balances.deleteModuleData(source as Module);
  }
  await purgeCache(source);
};

const purge = async (source: PurgeParams) => {
  set(confirm, false);
  try {
    set(pending, true);
    await purgeSource(source.source);
    set(status, {
      success: tc('data_management.success', 0, {
        source: source.text
      }),
      error: ''
    });
    setTimeout(() => set(status, null), 5000);
  } catch {
    set(status, {
      error: tc('data_management.error', 0, {
        source: source.text
      }),
      success: ''
    });
  } finally {
    set(pending, false);
  }
};
</script>
