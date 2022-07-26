<template>
  <setting-category>
    <template #title>
      {{ $t('data_management.title') }}
    </template>
    <template #subtitle>
      {{ $t('data_management.subtitle') }}
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
    <confirm-dialog
      v-if="confirm"
      display
      :title="$t('data_management.confirm.title')"
      :message="$t('data_management.confirm.message', { source: sourceLabel })"
      @confirm="purge(source)"
      @cancel="confirm = false"
    />
  </setting-category>
</template>
<script setup lang="ts">
import { ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import PurgeSelector, {
  PurgeParams
} from '@/components/settings/data-security/PurgeSelector.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { BaseMessage } from '@/components/settings/utils';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS
} from '@/services/session/consts';
import { Purgeable } from '@/services/session/types';
import { ACTION_PURGE_CACHED_DATA } from '@/store/session/const';
import { useStore } from '@/store/utils';
import { SUPPORTED_EXCHANGES, SupportedExchange } from '@/types/exchanges';
import { Module } from '@/types/modules';

const source = ref<Purgeable>(ALL_TRANSACTIONS);
const status = ref<BaseMessage | null>(null);
const confirm = ref<boolean>(false);
const pending = ref<boolean>(false);
const sourceLabel = ref<string>('');

const store = useStore();

const purgeCachedData = async (purgeable: Purgeable) => {
  await store.dispatch(`session/${ACTION_PURGE_CACHED_DATA}`, purgeable);
};

const showConfirmation = (source: PurgeParams) => {
  set(sourceLabel, source.text);
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
  } else {
    if (
      SUPPORTED_EXCHANGES.includes(source as any) ||
      EXTERNAL_EXCHANGES.includes(source as any)
    ) {
      await api.balances.deleteExchangeData(source as SupportedExchange);
    } else if (Object.values(Module).includes(source as any)) {
      await api.balances.deleteModuleData(source as Module);
    }
  }
  await purgeCachedData(source);
};

const purge = async (source: string) => {
  set(confirm, false);
  try {
    set(pending, true);
    await purgeSource(source);
    set(status, {
      success: i18n
        .t('data_management.success', {
          source: get(sourceLabel)
        })
        .toString(),
      error: ''
    });
    setTimeout(() => set(status, null), 5000);
  } catch (e: any) {
    set(status, {
      error: i18n
        .t('data_management.error', {
          source: get(sourceLabel)
        })
        .toString(),
      success: ''
    });
  } finally {
    set(pending, false);
  }
};
</script>
