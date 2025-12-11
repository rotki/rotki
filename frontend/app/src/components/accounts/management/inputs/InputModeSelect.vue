<script setup lang="ts">
import { assert } from '@rotki/common';
import { useAccountLoading } from '@/composables/accounts/loading';
import { isBtcChain } from '@/types/blockchain/chains';
import { InputMode } from '@/types/input-mode';
import { isOfEnum } from '@/utils';

const inputMode = defineModel<InputMode>('inputMode', { required: true });

const props = defineProps<{
  blockchain: string;
}>();

const internalValue = computed<string>({
  get() {
    return get(inputMode);
  },
  set(value: string) {
    assert(isOfEnum(InputMode)(value));
    set(inputMode, value);
  },
});

const isBitcoin = computed<boolean>(() => isBtcChain(props.blockchain));
const isXpub = computed<boolean>(() => get(inputMode) === InputMode.XPUB_ADD);

const { t } = useI18n({ useScope: 'global' });
const { isAccountOperationRunning } = useAccountLoading();
const loading = isAccountOperationRunning();

const invalidCombination = logicAnd(logicNot(isBitcoin), isXpub);

watch(invalidCombination, (invalid) => {
  if (invalid)
    set(inputMode, InputMode.MANUAL_ADD);
});

onUnmounted(() => {
  set(inputMode, InputMode.MANUAL_ADD);
});
</script>

<template>
  <div class="mb-5">
    <RuiButtonGroup
      v-model="internalValue"
      class="input-mode-select"
      variant="outlined"
      size="lg"
      required
      color="primary"
    >
      <RuiButton
        type="button"
        :model-value="InputMode.MANUAL_ADD"
        data-cy="input-mode-manual"
        :disabled="loading"
      >
        <template #prepend>
          <RuiIcon name="lu-pencil" />
        </template>
        <span class="hidden md:block">
          {{ t('input_mode_select.manual_add.label') }}
        </span>
      </RuiButton>
      <RuiButton
        v-if="isBitcoin"
        type="button"
        :model-value="InputMode.XPUB_ADD"
        :disabled="loading"
      >
        <template #prepend>
          <RuiIcon name="lu-key" />
        </template>
        <span class="hidden md:block">
          {{ t('input_mode_select.xpub_add.label') }}
        </span>
      </RuiButton>
    </RuiButtonGroup>
  </div>
</template>
