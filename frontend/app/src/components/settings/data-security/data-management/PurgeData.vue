<script setup lang="ts">
import { type Ref } from 'vue';
import { Module, SUPPORTED_MODULES } from '@/types/modules';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS,
  PURGABLE,
  type Purgeable
} from '@/types/session/purge';
import { SUPPORTED_EXCHANGES, type SupportedExchange } from '@/types/exchanges';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';

const source: Ref<Purgeable> = ref(ALL_TRANSACTIONS);

const { purgeCache } = useSessionPurge();

const { deleteModuleData } = useBlockchainBalancesApi();
const { deleteEvmTransactions } = useHistoryEventsApi();
const { deleteExchangeData } = useExchangeApi();

const purgeSource = async (source: Purgeable) => {
  if (source === ALL_TRANSACTIONS) {
    await deleteEvmTransactions(get(evmChainToClear));
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

const { t } = useI18n();
const { tradeLocations } = useLocations();

const text = (source: Purgeable) => {
  const location = get(tradeLocations).find(
    ({ identifier }) => identifier === source
  );

  if (location) {
    return t('purge_selector.exchange', {
      name: location.name
    });
  }

  const module = SUPPORTED_MODULES.find(
    ({ identifier }) => identifier === source
  );
  if (module) {
    return t('purge_selector.module', { name: module.name });
  }

  if (source === ALL_TRANSACTIONS) {
    return t('purge_selector.evm_transactions');
  } else if (source === ALL_CENTRALIZED_EXCHANGES) {
    return t('purge_selector.all_exchanges');
  } else if (source === ALL_MODULES) {
    return t('purge_selector.all_modules');
  } else if (source === ALL_DECENTRALIZED_EXCHANGES) {
    return t('purge_selector.all_decentralized_exchanges');
  }
  return source;
};

const purgable = PURGABLE.map(id => ({
  id,
  text: text(id)
})).sort((a, b) => (a.text < b.text ? -1 : 1));

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
  (source: string) => ({
    title: t('data_management.purge_data.confirm.title'),
    message:
      source === text(ALL_TRANSACTIONS)
        ? t('data_management.purge_data.evm_transaction_purge_confirm.message')
        : t('data_management.purge_data.confirm.message', {
            source
          })
  })
);

const evmChainToClear: Ref<string> = ref('');

const { txEvmChainsToLocation } = useSupportedChains();
</script>

<template>
  <div>
    <div class="mb-6">
      <div class="text-h6">
        {{ t('data_management.purge_data.title') }}
      </div>
      <div>
        {{ t('data_management.purge_data.subtitle') }}
      </div>
    </div>

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
          v-if="source === ALL_TRANSACTIONS"
          v-model="evmChainToClear"
          class="flex-1"
          required
          outlined
          clearable
          :items="txEvmChainsToLocation"
          :label="t('purge_selector.evm_chain_to_clear.label')"
          :hint="t('purge_selector.evm_chain_to_clear.hint')"
        />
      </div>
      <RuiTooltip :popper="{ placement: 'top' }" open-delay="400" class="-mt-8">
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
