<script setup lang="ts">
import LocationIcon from '@/components/history/LocationIcon.vue';

const modelValue = defineModel<boolean>({ required: true });

withDefaults(defineProps<{
  disabled?: boolean;
  chain: string;
}>(), {
  disabled: false,
});

function toggleSelect(): void {
  set(modelValue, !get(modelValue));
}
</script>

<template>
  <div
    class="flex items-center px-4 py-1 pr-2 cursor-pointer hover:bg-rui-grey-100 hover:dark:bg-rui-grey-900 transition"
    @click.prevent="toggleSelect()"
  >
    <RuiCheckbox
      v-model="modelValue"
      :disabled="disabled"
      color="primary"
      size="sm"
      hide-details
    />
    <LocationIcon
      size="1.25"
      class="text-sm"
      :item="chain"
      horizontal
    />
    <div class="grow" />
  </div>
</template>
