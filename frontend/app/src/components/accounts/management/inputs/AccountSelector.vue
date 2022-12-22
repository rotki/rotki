<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type InputMode } from '@/types/input-mode';
import Fragment from '@/components/helper/Fragment';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import InputModeSelect from '@/components/accounts/management/inputs/InputModeSelect.vue';

defineProps<{
  blockchain: Blockchain;
  inputMode: InputMode;
}>();

const emit = defineEmits<{
  (e: 'update:blockchain', selection: Blockchain): void;
  (e: 'update:input-mode', mode: InputMode): void;
}>();

const { loading } = useAccountLoading();
const { accountToEdit } = useAccountDialog();
</script>

<template>
  <fragment>
    <chain-select
      :disabled="loading || !!accountToEdit"
      :blockchain="blockchain"
      @update:blockchain="emit('update:blockchain', $event)"
    />

    <input-mode-select
      v-if="!accountToEdit"
      :input-mode="inputMode"
      :blockchain="blockchain"
      @update:input-mode="emit('update:input-mode', $event)"
    />
  </fragment>
</template>
