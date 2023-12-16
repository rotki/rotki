<script setup lang="ts">
import { DECENTRALIZED_EXCHANGES, Module } from '@/types/modules';
import { Purgeable } from '@/types/session/purge';

const modules = Object.values(Module);
const { allExchanges } = storeToRefs(useLocationStore());
const { txChains } = useSupportedChains();

const { purgeCache } = useSessionPurge();
const { deleteModuleData } = useBlockchainBalancesApi();
const { deleteTransactions } = useHistoryEventsApi();
const { deleteExchangeData } = useExchangeApi();

const { t } = useI18n();

const source = ref<Purgeable>(Purgeable.TRANSACTIONS);

const centralizedExchangeToClear = ref<string>('');
const decentralizedExchangeToClear = ref<string>('');
const chainToClear = ref<string>('');
const moduleToClear = ref<string>('');

const purgable = [
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
];

async function purgeSource(source: Purgeable) {
  const valueRef = purgable.find(({ id }) => id === source)?.value;
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
    else await Promise.all(DECENTRALIZED_EXCHANGES.map(deleteModuleData));
  }

  await purgeCache(source, value);
}

const { status, pending, showConfirmation } = useCacheClear<Purgeable>(
  purgable,
  purgeSource,
  (source: string) => ({
    success: t('data_management.purge_data.success', {
      source,
    }),
    error: t('data_management.purge_data.error', {
      source,
    }),
  }),
  (textSource, source) => {
    const valueRef = purgable.find(({ id }) => id === source)?.value;
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
      title: t('data_management.purge_data.confirm.title'),
      message,
    };
  },
);

const chainsSelection = useArrayMap(txChains, item => item.id);
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
        <RuiAutoComplete
          v-model="source"
          class="flex-1"
          variant="outlined"
          :label="t('purge_selector.label')"
          :options="purgable"
          text-attr="text"
          key-attr="id"
          :disabled="pending"
        />
        <ChainSelect
          v-if="source === Purgeable.TRANSACTIONS"
          v-model="chainToClear"
          class="flex-1"
          clearable
          persistent-hint
          :items="chainsSelection"
          :label="t('purge_selector.chain_to_clear.label')"
          :hint="t('purge_selector.chain_to_clear.hint')"
        />
        <LocationSelector
          v-else-if="source === Purgeable.CENTRALIZED_EXCHANGES"
          v-model="centralizedExchangeToClear"
          class="flex-1"
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
          :items="modules"
          :label="t('purge_selector.defi_module_to_clear.label')"
          :hint="t('purge_selector.defi_module_to_clear.hint')"
        />
      </div>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="-mt-6"
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

    <ActionStatusIndicator
      v-if="status"
      class="mt-4"
      :status="status"
    />
  </div>
</template>
