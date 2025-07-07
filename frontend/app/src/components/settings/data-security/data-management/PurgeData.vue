<script setup lang="ts">
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import DefiModuleSelector from '@/components/defi/DefiModuleSelector.vue';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useCacheClear } from '@/composables/session/cache-clear';
import { useSessionPurge } from '@/composables/session/purge';
import { useLocationStore } from '@/store/locations';
import { DECENTRALIZED_EXCHANGES, Module, PurgeableOnlyModule } from '@/types/modules';
import { Purgeable } from '@/types/session/purge';
import { toSentenceCase } from '@rotki/common';

const purgeableOnlyModules = Object.values(PurgeableOnlyModule);
const purgeableModules = [...Object.values(Module), ...purgeableOnlyModules];
const { allExchanges } = storeToRefs(useLocationStore());
const { allTxChainsInfo } = useSupportedChains();

const { purgeCache } = useSessionPurge();
const { deleteModuleData } = useBlockchainBalancesApi();
const { deleteStakeEvents, deleteTransactions } = useHistoryEventsApi();
const { deleteExchangeData } = useExchangeApi();

const { t } = useI18n({ useScope: 'global' });

const source = ref<Purgeable>(Purgeable.TRANSACTIONS);

const centralizedExchangeToClear = ref<string>('');
const decentralizedExchangeToClear = ref<string>('');
const chainToClear = ref<string>('');
const moduleToClear = ref<string>('');

const purgeable = [
  {
    id: Purgeable.CENTRALIZED_EXCHANGES,
    text: t('purge_selector.centralized_exchanges'),
    value: centralizedExchangeToClear,
  },
  {
    id: Purgeable.DECENTRALIZED_EXCHANGES,
    text: t('purge_selector.decentralized_exchanges'),
    value: decentralizedExchangeToClear,
  },
  {
    id: Purgeable.DEFI_MODULES,
    text: t('purge_selector.defi_modules'),
    value: moduleToClear,
  },
  {
    id: Purgeable.TRANSACTIONS,
    text: t('purge_selector.transactions'),
    value: chainToClear,
  },
  {
    id: Purgeable.ETH_WITHDRAWAL_EVENT,
    text: t('purge_selector.eth_withdrawals'),
  },
  {
    id: Purgeable.ETH_BLOCK_EVENT,
    text: t('purge_selector.eth_block'),
  },
];

async function purgeSource(source: Purgeable) {
  const valueRef = purgeable.find(({ id }) => id === source)?.value;
  const value = valueRef ? get(valueRef) : '';
  if (source === Purgeable.TRANSACTIONS) {
    await deleteTransactions(value);
  }
  else if (source === Purgeable.DEFI_MODULES) {
    await deleteModuleData((value as Module) || null);
  }
  else if (source === Purgeable.CENTRALIZED_EXCHANGES) {
    await deleteExchangeData(value);
  }
  else if (source === Purgeable.DECENTRALIZED_EXCHANGES) {
    if (value)
      await deleteModuleData(value as Module);
    else
      await Promise.all(DECENTRALIZED_EXCHANGES.map(deleteModuleData));
  }
  else if ([Purgeable.ETH_WITHDRAWAL_EVENT, Purgeable.ETH_BLOCK_EVENT].includes(source)) {
    await deleteStakeEvents(source);
  }

  // Purgeable only modules don't have some cache that needs reset.
  if (Array.prototype.includes.call(purgeableOnlyModules, value))
    return;

  purgeCache(source, value);
}

const { pending, showConfirmation, status } = useCacheClear<Purgeable>(
  purgeable,
  purgeSource,
  (source: string) => ({
    error: t('data_management.purge_data.error', {
      source,
    }),
    success: t('data_management.purge_data.success', {
      source,
    }),
  }),
  (textSource, source) => {
    const valueRef = purgeable.find(({ id }) => id === source)?.value;
    const value = valueRef ? get(valueRef) : '';

    let message = '';
    if (source === Purgeable.TRANSACTIONS) {
      message = t('data_management.purge_data.transaction_purge_confirm.message');
    }
    else if (value) {
      message = t('data_management.purge_data.confirm.message', {
        source: textSource,
        value: toSentenceCase(value),
      });
    }
    else {
      message = t('data_management.purge_data.confirm.message_all', {
        source: textSource,
      });
    }

    return {
      message,
      title: t('data_management.purge_data.confirm.title'),
    };
  },
);

const chainsSelection = useArrayMap(allTxChainsInfo, item => item.id);
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('data_management.purge_data.title') }}
    </template>
    <template #subtitle>
      {{ t('data_management.purge_data.subtitle') }}
    </template>
    <div class="flex flex-col gap-4">
      <RuiAutoComplete
        v-model="source"
        variant="outlined"
        :label="t('purge_selector.label')"
        :options="purgeable"
        text-attr="text"
        key-attr="id"
        hide-details
        :disabled="pending"
      />
      <ChainSelect
        v-if="source === Purgeable.TRANSACTIONS"
        v-model="chainToClear"
        clearable
        persistent-hint
        :items="chainsSelection"
        :label="t('purge_selector.chain_to_clear.label')"
        :hint="t('purge_selector.chain_to_clear.hint')"
      />
      <LocationSelector
        v-else-if="source === Purgeable.CENTRALIZED_EXCHANGES"
        v-model="centralizedExchangeToClear"
        clearable
        persistent-hint
        :items="allExchanges"
        :label="t('purge_selector.centralized_exchange_to_clear.label')"
        :hint="t('purge_selector.centralized_exchange_to_clear.hint')"
      />
      <LocationSelector
        v-else-if="source === Purgeable.DECENTRALIZED_EXCHANGES"
        v-model="decentralizedExchangeToClear"
        clearable
        persistent-hint
        :items="DECENTRALIZED_EXCHANGES"
        :label="t('purge_selector.decentralized_exchange_to_clear.label')"
        :hint="t('purge_selector.decentralized_exchange_to_clear.hint')"
      />
      <DefiModuleSelector
        v-else-if="source === Purgeable.DEFI_MODULES"
        v-model="moduleToClear"
        :items="purgeableModules"
        :label="t('purge_selector.defi_module_to_clear.label')"
        :hint="t('purge_selector.defi_module_to_clear.hint')"
      />

      <ActionStatusIndicator
        v-if="status"
        :status="status"
      />

      <div class="flex justify-end">
        <RuiButton
          :disabled="!source || pending"
          :loading="pending"
          color="error"
          @click="showConfirmation(source)"
        >
          <template #prepend>
            <RuiIcon
              name="lu-trash-2"
              size="16"
            />
          </template>

          {{ t('purge_selector.tooltip') }}
        </RuiButton>
      </div>
    </div>
  </SettingsItem>
</template>
