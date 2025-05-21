<script setup lang="ts">
import type { Exchange } from '@/types/exchanges';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { useSessionSettingsStore } from '@/store/settings/session';
import { isEqual, sortBy } from 'es-toolkit';

const modelValue = defineModel<Exchange[]>({ required: true });
const search = defineModel<string>('search', { required: true });

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ 'update:all-selected': [allSelected: boolean] }>();

const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

const filteredExchanges = computed<Exchange[]>(() => {
  const query = get(search).toLocaleLowerCase();
  return get(connectedExchanges).filter(exchange =>
    exchange.name.toLocaleLowerCase().includes(query) || exchange.location.toLocaleLowerCase().includes(query),
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

function toggleSelectAll() {
  if (get(modelValue).length > 0) {
    updateSelection([]);
  }
  else {
    updateSelection(get(connectedExchanges));
  }
}

function updateSelection(exchanges: Exchange[]) {
  set(modelValue, exchanges);
  emit('update:all-selected', isEqual(
    sortBy(exchanges, ['location', 'name']),
    sortBy(get(connectedExchanges), ['location', 'name']),
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
      @click.prevent.stop="toggleSelect(exchange)"
    />

    <LocationDisplay
      :identifier="exchange.location"
      icon
      :open-details="false"
      size="26px"
    />

    {{ exchange.name }}

    <div class="grow" />
  </div>
</template>
