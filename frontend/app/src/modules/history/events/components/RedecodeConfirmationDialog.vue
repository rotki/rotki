<script setup lang="ts">
import type { PullEventPayload } from '@/types/history/events';
import { HistoryEventEntryType } from '@rotki/common';
import PrioritizedList from '@/components/helper/PrioritizedList.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { EvmIndexer } from '@/types/settings/evm-indexer';
import { PrioritizedListData } from '@/types/settings/prioritized-list-data';
import {
  BLOCKSCOUT_PRIO_LIST_ITEM,
  ETHERSCAN_PRIO_LIST_ITEM,
  type PrioritizedListId,
  ROUTESCAN_PRIO_LIST_ITEM,
} from '@/types/settings/prioritized-list-id';

const show = defineModel<boolean>('show', { required: true });

const props = defineProps<{
  payload: PullEventPayload | undefined;
  hasCustomEvents?: boolean;
  showIndexerOptions?: boolean;
}>();

const emit = defineEmits<{
  confirm: [event: { payload: PullEventPayload; deleteCustom: boolean; customIndexersOrder?: string[] }];
}>();

const deleteCustom = ref<boolean>(false);
const localIndexerOrder = ref<PrioritizedListId[]>([]);

const { t } = useI18n({ useScope: 'global' });
const { getEvmChainName } = useSupportedChains();
const { defaultEvmIndexerOrder, evmIndexersOrder } = storeToRefs(useGeneralSettingsStore());

const availableIndexers = new PrioritizedListData<PrioritizedListId>([
  ETHERSCAN_PRIO_LIST_ITEM,
  BLOCKSCOUT_PRIO_LIST_ITEM,
  ROUTESCAN_PRIO_LIST_ITEM,
]);

const isEvmEvent = computed<boolean>(() => {
  const payload = props.payload;
  if (!payload)
    return false;

  return payload.type === HistoryEventEntryType.EVM_EVENT
    || payload.type === HistoryEventEntryType.EVM_SWAP_EVENT;
});

const evmChainName = computed<string | undefined>(() => {
  const payload = props.payload;
  if (!payload)
    return undefined;

  // Type guard: EVM events have LocationAndTxRef as data, ETH block events have number[]
  if (payload.type === HistoryEventEntryType.EVM_EVENT || payload.type === HistoryEventEntryType.EVM_SWAP_EVENT) {
    return getEvmChainName(payload.data.location);
  }

  return undefined;
});

function getInitialIndexerOrder(): PrioritizedListId[] {
  const chainName = get(evmChainName);
  const chainOrders = get(evmIndexersOrder);

  // Check for chain-specific order first
  if (chainName && chainOrders && chainOrders[chainName]) {
    return [...chainOrders[chainName]];
  }

  // Fall back to default order
  const defaultOrder = get(defaultEvmIndexerOrder);
  if (defaultOrder && defaultOrder.length > 0) {
    return [...defaultOrder];
  }

  // Use all indexers if no setting is configured
  return [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT, EvmIndexer.ROUTESCAN];
}

function resetState(): void {
  set(deleteCustom, false);
  set(localIndexerOrder, getInitialIndexerOrder());
}

function confirmRedecode(): void {
  const payload = props.payload;
  if (payload) {
    const indexerOrder = get(localIndexerOrder);
    emit('confirm', {
      customIndexersOrder: get(isEvmEvent) && indexerOrder.length > 0 ? indexerOrder : undefined,
      deleteCustom: get(deleteCustom),
      payload,
    });
  }
  set(show, false);
  resetState();
}

watch(show, (value) => {
  if (value) {
    resetState();
  }
});
</script>

<template>
  <RuiDialog
    v-model="show"
    :max-width="700"
  >
    <RuiCard content-class="!pt-0">
      <template #header>
        {{ t('transactions.actions.redecode_events') }}
      </template>

      <!-- Custom events section - only show when there are custom events -->
      <SettingsItem
        v-if="hasCustomEvents"
        class="!pt-0 pb-6"
        :class="{ '!border-0 !pb-0': !showIndexerOptions || !isEvmEvent }"
      >
        <template #title>
          {{ t('transactions.events.confirmation.reset.custom_events_title') }}
        </template>
        <template #subtitle>
          {{ t('transactions.events.confirmation.reset.message') }}
        </template>
        <RuiRadioGroup
          v-model="deleteCustom"
          color="primary"
          :hide-details="true"
          size="sm"
        >
          <RuiRadio :value="false">
            <span class="text-sm">{{ t('transactions.events.confirmation.reset.options.keep_custom_events') }}</span>
          </RuiRadio>
          <RuiRadio
            :value="true"
            class="-my-2"
          >
            <span class="text-sm">{{ t('transactions.events.confirmation.reset.options.remove_custom_events') }}</span>
          </RuiRadio>
        </RuiRadioGroup>
      </SettingsItem>

      <!-- Indexer order section for EVM events (only when showIndexerOptions is true) -->
      <SettingsItem
        v-if="showIndexerOptions && isEvmEvent"
        class="!py-0 !border-0"
        :class="{ '!pt-4': hasCustomEvents }"
      >
        <template #title>
          {{ t('transactions.events.confirmation.reset.indexer_order_title') }}
        </template>
        <template #subtitle>
          {{ t('transactions.events.confirmation.reset.indexer_order_hint') }}
        </template>
        <RuiAlert
          v-if="localIndexerOrder.length === 0"
          type="warning"
          class="mb-4"
        >
          {{ t('evm_settings.indexer.no_indexers_warning') }}
        </RuiAlert>
        <PrioritizedList
          v-model="localIndexerOrder"
          dense
          :all-items="availableIndexers"
          :item-data-name="t('evm_settings.indexer.data_name')"
          :disable-delete="localIndexerOrder.length <= 1"
          variant="flat"
        />
      </SettingsItem>

      <template #footer>
        <div class="grow" />
        <RuiButton
          color="primary"
          @click="confirmRedecode()"
        >
          {{ t('common.actions.proceed') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
