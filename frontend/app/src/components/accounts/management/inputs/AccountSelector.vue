<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import Fragment from '@/components/helper/Fragment';
import { isBtcChain } from '@/types/blockchain/chains';
import { type InputMode } from '@/types/input-mode';

const props = defineProps<{
  blockchain: Blockchain;
  inputMode: InputMode;
}>();

const emit = defineEmits<{
  (e: 'update:blockchain', selection: Blockchain): void;
  (e: 'update:input-mode', mode: InputMode): void;
}>();

const blockchain = toRef(props, 'blockchain');

const { loading } = useAccountLoading();
const { accountToEdit } = useAccountDialog();
const { isEvm } = useSupportedChains();

const isEvmChain = isEvm(blockchain);

const showInputModeSelector = logicOr(
  computed(() => isBtcChain(get(blockchain))),
  isEvmChain
);
</script>

<template>
  <fragment>
    <chain-select
      :disabled="loading || !!accountToEdit"
      :model-value="blockchain"
      @update:model-value="emit('update:blockchain', $event)"
    />

    <input-mode-select
      v-if="!accountToEdit && showInputModeSelector"
      :input-mode="inputMode"
      :blockchain="blockchain"
      @update:input-mode="emit('update:input-mode', $event)"
    />
  </fragment>
</template>
