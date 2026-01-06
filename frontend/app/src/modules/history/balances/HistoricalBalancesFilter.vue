<script setup lang="ts">
import type { LocationLabel } from '@/types/location';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import LocationLabelSelector from '@/components/history/LocationLabelSelector.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import CounterpartyInput from '@/components/inputs/CounterpartyInput.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
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

const { t } = useI18n({ useScope: 'global' });

const historyStore = useHistoryStore();
const { fetchLocationLabels } = historyStore;
const { locationLabels: allLocationLabels } = storeToRefs(historyStore);

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
  <div class="grid grid-cols-1 md:grid-cols-6 gap-4 mb-4">
    <DateTimePicker
      v-model="timestamp"
      variant="outlined"
      :label="t('historical_balances.timestamp_label')"
      max-date="now"
      type="epoch"
      accuracy="second"
      class="md:col-span-3"
    />

    <AssetSelect
      v-model="selectedAsset"
      clearable
      variant="outlined"
      class="md:col-span-3"
      :hint="t('historical_balances.asset_hint')"
    />

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
  </div>
</template>
