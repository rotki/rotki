<script setup lang="ts">
import { type Ref } from 'vue';
import { type BaseMessage } from '@/types/messages';
import { Module, SUPPORTED_MODULES } from '@/types/modules';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS,
  PURGABLE,
  type PurgeParams,
  type Purgeable
} from '@/types/session/purge';
import { SUPPORTED_EXCHANGES, type SupportedExchange } from '@/types/exchanges';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';

const source: Ref<Purgeable> = ref(ALL_TRANSACTIONS);
const status: Ref<BaseMessage | null> = ref(null);
const confirm: Ref<boolean> = ref(false);
const pending: Ref<boolean> = ref(false);

const { purgeCache } = useSessionPurge();

const { show } = useConfirmStore();

const showConfirmation = (source: PurgeParams) => {
  show(
    {
      title: tc('data_management.purge_data.confirm.title'),
      message: tc('data_management.purge_data.confirm.message', 0, {
        source: source.text
      })
    },
    async () => purge(source)
  );
  set(confirm, true);
};

const { deleteModuleData } = useBlockchainBalancesApi();
const { deleteEthTransactions } = useTransactionsApi();
const { deleteExchangeData } = useExchangeApi();

const purgeSource = async (source: Purgeable) => {
  if (source === ALL_TRANSACTIONS) {
    await deleteEthTransactions();
  } else if (source === ALL_MODULES) {
    await deleteModuleData();
  } else if (source === ALL_CENTRALIZED_EXCHANGES) {
    await deleteExchangeData();
  } else if (source === ALL_DECENTRALIZED_EXCHANGES) {
    await Promise.all([
      deleteModuleData(Module.UNISWAP),
      deleteModuleData(Module.BALANCER)
    ]);
  } else if (
    SUPPORTED_EXCHANGES.includes(source as any) ||
    EXTERNAL_EXCHANGES.includes(source as any)
  ) {
    await deleteExchangeData(source as SupportedExchange);
  } else if (Object.values(Module).includes(source as any)) {
    await deleteModuleData(source as Module);
  }
  await purgeCache(source);
};

const purge = async (source: PurgeParams) => {
  set(confirm, false);
  try {
    set(pending, true);
    await purgeSource(source.source);
    set(status, {
      success: tc('data_management.purge_data.success', 0, {
        source: source.text
      }),
      error: ''
    });
    setTimeout(() => set(status, null), 5000);
  } catch {
    set(status, {
      error: tc('data_management.purge_data.error', 0, {
        source: source.text
      }),
      success: ''
    });
  } finally {
    set(pending, false);
  }
};

const { tc } = useI18n();
const { tradeLocations } = useTradeLocations();

const text = (source: Purgeable) => {
  const location = get(tradeLocations).find(
    ({ identifier }) => identifier === source
  );
  if (location) {
    return tc('purge_selector.exchange', 0, {
      name: location.name
    });
  }

  const module = SUPPORTED_MODULES.find(
    ({ identifier }) => identifier === source
  );
  if (module) {
    return tc('purge_selector.module', 0, { name: module.name });
  }

  if (source === ALL_TRANSACTIONS) {
    return tc('purge_selector.ethereum_transactions');
  } else if (source === ALL_CENTRALIZED_EXCHANGES) {
    return tc('purge_selector.all_exchanges');
  } else if (source === ALL_MODULES) {
    return tc('purge_selector.all_modules');
  } else if (source === ALL_DECENTRALIZED_EXCHANGES) {
    return tc('purge_selector.all_decentralized_exchanges');
  }
  return source;
};

const purgable = PURGABLE.map(id => ({
  id,
  text: text(id)
})).sort((a, b) => (a.text < b.text ? -1 : 1));
</script>

<template>
  <div>
    <div class="mb-6">
      <div class="text-h6">
        {{ tc('data_management.purge_data.title') }}
      </div>
      <div>
        {{ tc('data_management.purge_data.subtitle') }}
      </div>
    </div>

    <v-row class="mb-0" align="center">
      <v-col>
        <v-autocomplete
          v-model="source"
          outlined
          :label="tc('purge_selector.label')"
          :items="purgable"
          item-text="text"
          item-value="id"
          :disabled="pending"
          hide-details
        />
      </v-col>
      <v-col cols="auto">
        <v-tooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <v-btn
              v-bind="attrs"
              icon
              :disabled="!source || pending"
              :loading="pending"
              v-on="on"
              @click="showConfirmation({ source: source, text: text(source) })"
            >
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </template>
          <span> {{ tc('purge_selector.tooltip') }} </span>
        </v-tooltip>
      </v-col>
    </v-row>

    <action-status-indicator v-if="status" :status="status" />
  </div>
</template>
