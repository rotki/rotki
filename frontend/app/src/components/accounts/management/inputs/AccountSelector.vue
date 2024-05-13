<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { isBtcChain } from '@/types/blockchain/chains';
import type { InputMode } from '@/types/input-mode';

const props = defineProps<{
  chain: string;
  inputMode: InputMode;
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:chain', selection: string): void;
  (e: 'update:input-mode', mode: InputMode): void;
}>();

const chain = toRef(props, 'chain');

const { loading } = useAccountLoading();
const { isEvm } = useSupportedChains();

const isEvmChain = isEvm(chain);

const showInputModeSelector = logicOr(
  computed(() => isBtcChain(get(chain))),
  isEvmChain,
);

function updateModelValue(value: string | null) {
  if (!value)
    return;

  emit('update:chain', value);
}
</script>

<template>
  <Fragment>
    <ChainSelect
      :disabled="loading || editMode"
      :model-value="chain"
      :clearable="false"
      @update:model-value="updateModelValue($event)"
    />

    <InputModeSelect
      v-if="!editMode && showInputModeSelector"
      :input-mode="inputMode"
      :blockchain="chain"
      @update:input-mode="emit('update:input-mode', $event)"
    />
  </Fragment>
</template>
