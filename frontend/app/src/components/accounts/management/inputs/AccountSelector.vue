<script setup lang="ts">
import type { InputMode } from '@/types/input-mode';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import InputModeSelect from '@/components/accounts/management/inputs/InputModeSelect.vue';
import { useAccountLoading } from '@/composables/accounts/loading';
import { isBtcChain } from '@/types/blockchain/chains';

const chain = defineModel<string>('chain', { required: true });
const inputMode = defineModel<InputMode>('inputMode', { required: true });

defineProps<{
  editMode: boolean;
  chainIds: string[];
}>();

const { loading } = useAccountLoading();

const showInputModeSelector = logicOr(
  computed<boolean>(() => isBtcChain(get(chain))),
);
</script>

<template>
  <ChainSelect
    v-model="chain"
    :disabled="loading || editMode"
    :items="chainIds"
  />

  <InputModeSelect
    v-if="!editMode && showInputModeSelector"
    v-model:input-mode="inputMode"
    :blockchain="chain"
  />
</template>
