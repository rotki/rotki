<script setup lang="ts">
import AccountDisplay from '@/components/display/AccountDisplay.vue';

const modelValue = defineModel<string[]>({ required: true });

const props = defineProps<{
  addresses: string[];
  chain: string;
  processing: boolean;
  search: string;
}>();

const filteredAddresses = computed<string[]>(() => props.addresses.filter(matchesSearch));

function matchesSearch(address: string): boolean {
  return address.toLocaleLowerCase().includes(props.search.toLocaleLowerCase());
}

function toggleSelect(address: string): void {
  const model = get(modelValue);
  if (model.includes(address)) {
    set(modelValue, model.filter(item => item !== address));
  }
  else {
    set(modelValue, [...model, address]);
  }
}
</script>

<template>
  <div
    v-for="address in filteredAddresses"
    :key="address"
    class="flex items-center px-4 py-1 pr-2 cursor-pointer hover:bg-rui-grey-100 hover:dark:bg-rui-grey-900 transition"
    @click="toggleSelect(address)"
  >
    <RuiCheckbox
      :model-value="modelValue.includes(address)"
      :disabled="processing"
      color="primary"
      size="sm"
      hide-details
      @click.prevent.stop="toggleSelect(address)"
    />

    <AccountDisplay
      :account="{
        address,
        chain,
      }"
    />

    <div class="grow" />
  </div>
</template>
