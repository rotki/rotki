<script setup lang="ts">
import type { EvmChainInfo } from '@/types/api/chains';
import type { Account } from '@rotki/common';
import LocationIcon from '@/components/history/LocationIcon.vue';

const modelValue = defineModel<Account[]>({ required: true });

defineProps<{
  item: EvmChainInfo;
  addresses: string[];
  processing: boolean;
}>();

const emit = defineEmits <{
  'select-all': [];
}>();
</script>

<template>
  <RuiCheckbox
    :model-value="modelValue.length === addresses.length"
    :indeterminate="modelValue.length > 0 && modelValue.length < addresses.length"
    :disabled="processing"
    color="primary"
    size="sm"
    hide-details
    @click.prevent.stop="emit('select-all')"
  />
  <LocationIcon
    size="1.25"
    class="text-sm"
    :item="item.evmChainName"
    horizontal
  />
  <div class="grow" />
  <TransitionGroup
    enter-active-class="opacity-100"
    leave-active-class="opacity-0"
  />
</template>
