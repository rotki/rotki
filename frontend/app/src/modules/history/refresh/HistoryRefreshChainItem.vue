<script setup lang="ts">
import type { ChainData } from '@/modules/history/refresh/types';
import LocationIcon from '@/components/history/LocationIcon.vue';

const modelValue = defineModel<string[]>({ required: true });

const props = defineProps<{
  item: ChainData;
  addresses: string[];
  processing: boolean;
}>();

const emit = defineEmits<{
  'pick-addresses': [chain: string];
}>();

function toggleSelect(): void {
  if (get(modelValue).length > 0) {
    set(modelValue, []);
  }
  else {
    set(modelValue, props.addresses);
  }
}
</script>

<template>
  <div
    class="flex items-center px-4 py-1 pr-2 cursor-pointer hover:bg-rui-grey-100 hover:dark:bg-rui-grey-900 transition"
    @click.prevent="emit('pick-addresses', item.evmChain)"
  >
    <RuiCheckbox
      :model-value="modelValue.length === addresses.length"
      :indeterminate="modelValue.length > 0 && modelValue.length < addresses.length"
      :disabled="processing"
      color="primary"
      size="sm"
      hide-details
      @click.prevent.stop="toggleSelect()"
    />
    <LocationIcon
      size="1.25"
      class="text-sm"
      :item="item.evmChain"
      horizontal
    />
    <div class="grow" />
    <RuiIcon
      name="lu-chevron-right"
      class="mx-2 text-rui-text-secondary"
    />
  </div>
</template>
