<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { isBtcChain } from '@/types/blockchain/chains';
import type { InputMode } from '@/types/input-mode';

const props = defineProps<{
  blockchain: string;
  inputMode: InputMode;
}>();

const emit = defineEmits<{
  (e: 'update:blockchain', selection: string): void;
  (e: 'update:input-mode', mode: InputMode): void;
}>();

const blockchain = toRef(props, 'blockchain');

const { loading } = useAccountLoading();
const { accountToEdit } = useAccountDialog();
const { isEvm } = useSupportedChains();

const isEvmChain = isEvm(blockchain);

const showInputModeSelector = logicOr(
  computed(() => isBtcChain(get(blockchain))),
  isEvmChain,
);

function updateModelValue(value: string | null) {
  if (!value)
    return;

  emit('update:blockchain', value);
}
</script>

<template>
  <Fragment>
    <ChainSelect
      :disabled="loading || !!accountToEdit"
      :model-value="blockchain"
      :clearable="false"
      @update:model-value="updateModelValue($event)"
    />

    <InputModeSelect
      v-if="!accountToEdit && showInputModeSelector"
      :input-mode="inputMode"
      :blockchain="blockchain"
      @update:input-mode="emit('update:input-mode', $event)"
    />
  </Fragment>
</template>
