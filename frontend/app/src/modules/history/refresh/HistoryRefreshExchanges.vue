<script setup lang="ts">
import type { Exchange } from '@/types/exchanges';
import { getTextToken } from '@rotki/common';
import { isEqual, sortBy } from 'es-toolkit';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useGeneralSettingsStore } from '@/store/settings/general';

const modelValue = defineModel<Exchange[]>({ required: true });
const search = defineModel<string>('search', { required: true });

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ 'update:all-selected': [allSelected: boolean] }>();

const { t } = useI18n({ useScope: 'global' });

const { syncingExchanges } = useExchangeData();
const { nonSyncingExchanges } = storeToRefs(useGeneralSettingsStore());

const hasNonSyncingExchanges = computed<boolean>(() => get(nonSyncingExchanges).length > 0);

const filteredExchanges = computed<Exchange[]>(() => {
  const query = getTextToken(get(search));
  return get(syncingExchanges).filter(exchange =>
    getTextToken(exchange.name).includes(query) || getTextToken(exchange.location).includes(query),
  );
});

function toggleSelect(exchange: Exchange): void {
  const model = get(modelValue);
  if (model.includes(exchange)) {
    updateSelection(model.filter(item => item !== exchange));
  }
  else {
    updateSelection([...model, exchange]);
  }
}

function toggleSelectAll(): void {
  if (get(modelValue).length > 0) {
    updateSelection([]);
  }
  else {
    updateSelection(get(syncingExchanges));
  }
}

function updateSelection(exchanges: Exchange[]): void {
  set(modelValue, exchanges);
  emit('update:all-selected', isEqual(
    sortBy(exchanges, ['location', 'name']),
    sortBy(get(syncingExchanges), ['location', 'name']),
  ));
}

defineExpose({
  toggleSelectAll,
});
</script>

<template>
  <div
    v-for="exchange in filteredExchanges"
    :key="exchange.name"
    class="flex items-center px-4 py-1 pr-2 cursor-pointer hover:bg-rui-grey-100 hover:dark:bg-rui-grey-900 transition"
    @click="toggleSelect(exchange)"
  >
    <RuiCheckbox
      :model-value="modelValue.includes(exchange)"
      :disabled="processing"
      color="primary"
      size="sm"
      hide-details
      @click.prevent
    />

    <LocationDisplay
      :identifier="exchange.location"
      icon
      :open-details="false"
      size="20px"
    />

    <span class="ml-2 text-rui-text-secondary text-sm capitalize">
      {{ exchange.name }}
    </span>

    <div class="grow" />
  </div>

  <div
    v-if="hasNonSyncingExchanges"
    class="px-4 py-2 text-xs text-rui-text-secondary italic"
  >
    {{ t('history_refresh_selection.non_syncing_hint', { count: nonSyncingExchanges.length }) }}
  </div>
</template>
