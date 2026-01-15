<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { LocationLabel } from '@/types/location';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import LocationLabelSelector from '@/components/history/LocationLabelSelector.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import CounterpartyInput from '@/components/inputs/CounterpartyInput.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useSupportedChains } from '@/composables/info/chains';
import {
  type HistoricalBalanceSource,
  HistoricalBalanceSource as Source,
} from '@/modules/history/balances/types';
import { useHistoryStore } from '@/store/history';

const timestamp = defineModel<number>('timestamp', { required: true });
const selectedAsset = defineModel<string>('selectedAsset');
const selectedLocation = defineModel<string>('selectedLocation', {
  required: true,
  set: (val: string | undefined) => val ?? '',
});
const selectedLocationLabel = defineModel<string>('selectedLocationLabel', {
  required: true,
  set: (val: string | undefined) => val ?? '',
});
const selectedProtocol = defineModel<string>('selectedProtocol');
const source = defineModel<HistoricalBalanceSource>('source', { required: true });
const selectedAccount = defineModel<BlockchainAccount<AddressData>>('selectedAccount');

const props = withDefaults(defineProps<{
  fieldErrors?: ValidationErrors;
}>(), {
  fieldErrors: () => ({}),
});

const { t } = useI18n({ useScope: 'global' });

const assetErrors = computed<string[]>(() => {
  const errors = props.fieldErrors.asset;
  if (!errors)
    return [];
  return Array.isArray(errors) ? errors : [errors];
});

const historyStore = useHistoryStore();
const { fetchLocationLabels } = historyStore;
const { locationLabels: allLocationLabels } = storeToRefs(historyStore);

const { txEvmChains } = useSupportedChains();

const isArchiveNodeSource = computed<boolean>(() => get(source) === Source.ARCHIVE_NODE);

const evmChainIds = computed<string[]>(() => get(txEvmChains).map(chain => chain.id));

const accountArray = computed<BlockchainAccount<AddressData>[]>({
  get: () => {
    const account = get(selectedAccount);
    return account ? [account] : [];
  },
  set: (val: BlockchainAccount<AddressData>[]) => {
    set(selectedAccount, val[0]);
  },
});

const selectedChain = computed<string | undefined>(() => {
  if (get(isArchiveNodeSource)) {
    const account = get(selectedAccount);
    return account?.chain;
  }

  return get(selectedLocation);
});

const sourceOptions = computed<{ value: HistoricalBalanceSource; label: string }[]>(() => [
  { label: t('historical_balances.source.historical_events'), value: Source.HISTORICAL_EVENTS },
  { label: t('historical_balances.source.archive_node'), value: Source.ARCHIVE_NODE },
]);

const availableLocations = computed<string[]>(() => {
  const labels = get(allLocationLabels);
  return [...new Set(labels.map(label => label.location))];
});

const filteredLocationLabels = computed<LocationLabel[]>(() => {
  const labels = get(allLocationLabels);
  const location = get(selectedLocation);

  if (!location)
    return labels;

  return labels.filter(label => label.location === location);
});

// Reset location label when location changes and it's no longer valid
watch(selectedLocation, () => {
  const currentLabel = get(selectedLocationLabel);
  if (!currentLabel)
    return;

  const validLabels = get(filteredLocationLabels);
  const isStillValid = validLabels.some(label => label.locationLabel === currentLabel);

  if (!isStillValid)
    set(selectedLocationLabel, '');
});

onBeforeMount(() => {
  fetchLocationLabels();
});
</script>

<template>
  <div class="flex flex-col gap-4 mb-4">
    <div class="mb-4 flex flex-col gap-2 items-start">
      <div class="text-body-2 text-rui-text-secondary">
        {{ t('historical_balances.source.label') }}
      </div>
      <RuiButtonGroup
        v-model="source"
        variant="outlined"
        color="primary"
      >
        <RuiButton
          v-for="option in sourceOptions"
          :key="option.value"
          :model-value="option.value"
        >
          {{ option.label }}
        </RuiButton>
      </RuiButtonGroup>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-6 gap-4">
      <DateTimePicker
        v-model="timestamp"
        variant="outlined"
        :label="t('historical_balances.timestamp_label')"
        max-date="now"
        type="epoch"
        required
        accuracy="second"
        class="md:col-span-3"
      />

      <AssetSelect
        v-model="selectedAsset"
        :clearable="!isArchiveNodeSource"
        variant="outlined"
        required
        class="md:col-span-3"
        :hint="isArchiveNodeSource ? t('historical_balances.asset_required_hint') : t('historical_balances.asset_hint')"
        :error-messages="assetErrors"
        :chain="selectedChain"
      />

      <BlockchainAccountSelector
        v-if="isArchiveNodeSource"
        v-model="accountArray"
        :chains="evmChainIds"
        class="md:col-span-4"
        :label="t('historical_balances.account')"
        :custom-hint="t('historical_balances.account_hint')"
        show-details
        outlined
        required
      />

      <template v-else>
        <LocationSelector
          v-model="selectedLocation"
          :items="availableLocations"
          clearable
          class="md:col-span-2"
          :label="t('common.location')"
          :hint="t('historical_balances.location_hint')"
        />

        <LocationLabelSelector
          v-model="selectedLocationLabel"
          :options="filteredLocationLabels"
          class="md:col-span-2"
          :label="t('historical_balances.location_label')"
          :hint="t('historical_balances.location_label_hint')"
          :no-data-text="t('historical_balances.no_location_labels')"
        />

        <CounterpartyInput
          v-model="selectedProtocol"
          class="md:col-span-2"
          :label="t('common.counterparty')"
          :hint="t('historical_balances.protocol_hint')"
        />
      </template>
    </div>
  </div>
</template>
