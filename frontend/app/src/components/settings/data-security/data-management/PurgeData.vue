<script setup lang="ts">
import { type Ref } from 'vue';
import { DECENTRALIZED_EXCHANGES, Module } from '@/types/modules';
import { Purgeable } from '@/types/session/purge';

const modules = Object.values(Module);
const { allExchanges } = storeToRefs(useLocationStore());
const { txEvmChainsToLocation } = useSupportedChains();

const { purgeCache } = useSessionPurge();
const { deleteModuleData } = useBlockchainBalancesApi();
const { deleteEvmTransactions } = useHistoryEventsApi();
const { deleteExchangeData } = useExchangeApi();

const { t } = useI18n();

const source: Ref<Purgeable> = ref(Purgeable.EVM_TRANSACTIONS);

const centralizedExchangeToClear: Ref<string> = ref('');
const decentralizedExchangeToClear: Ref<string> = ref('');
const evmChainToClear: Ref<string> = ref('');
const moduleToClear: Ref<string> = ref('');

const purgable = [
  {
    id: Purgeable.CENTRALIZED_EXCHANGES,
    text: t('purge_selector.centralized_exchanges'),
    value: centralizedExchangeToClear
  },
  {
    id: Purgeable.DECENTRALIZED_EXCHANGES,
    text: t('purge_selector.decentralized_exchanges'),
    value: decentralizedExchangeToClear
  },
  {
    id: Purgeable.DEFI_MODULES,
    text: t('purge_selector.defi_modules'),
    value: moduleToClear
  },
  {
    id: Purgeable.EVM_TRANSACTIONS,
    text: t('purge_selector.evm_transactions'),
    value: evmChainToClear
  }
];

const purgeSource = async (source: Purgeable) => {
  const valueRef = purgable.find(({ id }) => id === source)?.value;
  const value = valueRef ? get(valueRef) : '';
  if (source === Purgeable.EVM_TRANSACTIONS) {
    await deleteEvmTransactions(value);
  } else if (source === Purgeable.DEFI_MODULES) {
    await deleteModuleData((value as Module) || null);
  } else if (source === Purgeable.CENTRALIZED_EXCHANGES) {
    await deleteExchangeData(value);
  } else if (source === Purgeable.DECENTRALIZED_EXCHANGES) {
    if (value) {
      await deleteModuleData(value as Module);
    } else {
      await Promise.all(DECENTRALIZED_EXCHANGES.map(deleteModuleData));
    }
  }

  await purgeCache(source, value);
};

const { status, pending, showConfirmation } = useCacheClear<Purgeable>(
  purgable,
  purgeSource,
  (source: string) => ({
    success: t('data_management.purge_data.success', {
      source
    }),
    error: t('data_management.purge_data.error', {
      source
    })
  }),
  (textSource, source) => {
    const valueRef = purgable.find(({ id }) => id === source)?.value;
    const value = valueRef ? get(valueRef) : '';

    let message = '';
    if (source === Purgeable.EVM_TRANSACTIONS) {
      message = t(
        'data_management.purge_data.evm_transaction_purge_confirm.message'
      );
    } else if (value) {
      message = t('data_management.purge_data.confirm.message', {
        source: textSource,
        value: toSentenceCase(value)
      });
    } else {
      message = t('data_management.purge_data.confirm.message_all', {
        source: textSource
      });
    }

    return {
      title: t('data_management.purge_data.confirm.title'),
      message
    };
  }
);
</script>

<template>
  <div>
    <RuiCardHeader class="p-0 mb-4">
      <template #header>
        {{ t('data_management.purge_data.title') }}
      </template>
      <template #subheader>
        {{ t('data_management.purge_data.subtitle') }}
      </template>
    </RuiCardHeader>

    <div class="flex items-center gap-4">
      <div class="flex flex-col md:flex-row md:gap-4 flex-1">
        <VAutocomplete
          v-model="source"
          class="flex-1"
          outlined
          :label="t('purge_selector.label')"
          :items="purgable"
          item-text="text"
          item-value="id"
          :disabled="pending"
        />
        <LocationSelector
          v-if="source === Purgeable.EVM_TRANSACTIONS"
          v-model="evmChainToClear"
          class="flex-1"
          required
          outlined
          clearable
          persistent-hint
          :items="txEvmChainsToLocation"
          :label="t('purge_selector.evm_chain_to_clear.label')"
          :hint="t('purge_selector.evm_chain_to_clear.hint')"
        />
        <LocationSelector
          v-else-if="source === Purgeable.CENTRALIZED_EXCHANGES"
          v-model="centralizedExchangeToClear"
          class="flex-1"
          required
          outlined
          clearable
          persistent-hint
          :items="allExchanges"
          :label="t('purge_selector.centralized_exchange_to_clear.label')"
          :hint="t('purge_selector.centralized_exchange_to_clear.hint')"
        />
        <LocationSelector
          v-else-if="source === Purgeable.DECENTRALIZED_EXCHANGES"
          v-model="decentralizedExchangeToClear"
          class="flex-1"
          required
          outlined
          clearable
          persistent-hint
          :items="DECENTRALIZED_EXCHANGES"
          :label="t('purge_selector.decentralized_exchange_to_clear.label')"
          :hint="t('purge_selector.decentralized_exchange_to_clear.hint')"
        />
        <DefiModuleSelector
          v-else-if="source === Purgeable.DEFI_MODULES"
          v-model="moduleToClear"
          class="flex-1"
          required
          outlined
          clearable
          persistent-hint
          :items="modules"
          :label="t('purge_selector.defi_module_to_clear.label')"
          :hint="t('purge_selector.defi_module_to_clear.hint')"
        />
      </div>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="-mt-8"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            :disabled="!source || pending"
            :loading="pending"
            @click="showConfirmation(source)"
          >
            <RuiIcon name="delete-bin-line" />
          </RuiButton>
        </template>
        <span> {{ t('purge_selector.tooltip') }} </span>
      </RuiTooltip>
    </div>

    <ActionStatusIndicator v-if="status" :status="status" />
  </div>
</template>
