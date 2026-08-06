<script setup lang="ts">
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { BlockchainRpcNodeManageState } from '@/modules/settings/types/rpc';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { useForm } from '@/modules/core/form/use-form';
import {
  type BlockchainRpcNodeFormState,
  blockchainRpcNodeSchema,
  isEtherscanNode,
  MAX_WEIGHT,
  MIN_WEIGHT,
  stateFromNode,
  toNodeFields,
  toWeight,
} from '@/modules/settings/general/rpc/blockchain-rpc-node-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const modelValue = defineModel<BlockchainRpcNodeManageState>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => blockchainRpcNodeSchema({
  endpointRequired: t('settings.validation.text.non_empty'),
  nameRequired: t('settings.validation.text.non_empty'),
  weightBetween: t('settings.validation.number.between', { max: MAX_WEIGHT, min: MIN_WEIGHT }),
  weightRequired: t('settings.validation.number.non_empty'),
}));

/** The dialog owns the persist and reads the node off the model, so submitting here is a no-op. */
const form = useForm<BlockchainRpcNodeFormState, BlockchainRpcNodeFormState>({
  initial: (): BlockchainRpcNodeFormState => stateFromNode(get(modelValue).node),
  schema,
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): BlockchainRpcNodeFormState => ({ ...state }),
});

const isEtherscan = computed<boolean>(() => isEtherscanNode(form.state));

/** The slider edits the weight as a number, the field next to it as text. */
const numericWeight = computed<number>({
  get() {
    return toWeight(form.state.weight);
  },
  set(value: number) {
    form.state.weight = value.toString();
  },
});

// The dialog reads the node it saves straight off the model, so every edit is written back to it.
watch(() => form.state, (state) => {
  const current = get(modelValue);
  set(modelValue, {
    ...current,
    node: { ...current.node, ...toNodeFields(state) },
  });
}, { deep: true });

watch(errors, (value) => {
  form.setServerErrors(toServerErrors(value));
}, { deep: true });

watch(form.dirty, (dirty) => {
  set(stateUpdated, dirty);
});

// The dialog keeps its prompt-on-close flag across opens, so hand it back disarmed.
onUnmounted(() => {
  set(stateUpdated, false);
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <RuiTextField
      v-model="form.state.name"
      variant="outlined"
      color="primary"
      data-cy="node-name"
      :disabled="isEtherscan"
      :label="t('common.name')"
      :error-messages="form.errors('name')"
      @blur="form.touch('name')"
    />
    <RuiTextField
      v-model="form.state.endpoint"
      variant="outlined"
      color="primary"
      data-cy="node-endpoint"
      :disabled="isEtherscan"
      :error-messages="form.errors('endpoint')"
      :label="t('rpc_node_form.endpoint')"
      @blur="form.touch('endpoint')"
    />

    <div class="flex items-center gap-4">
      <RuiSlider
        v-model="numericWeight"
        class="flex-1"
        :disabled="form.state.owned"
        :error-messages="form.errors('weight')"
        :label="t('rpc_node_form.weight')"
        :min="MIN_WEIGHT"
        :max="MAX_WEIGHT"
        :hint="t('rpc_node_form.weight_hint', { weight: form.state.weight })"
        :step="1"
        show-thumb-label
        @blur="form.touch('weight')"
      />
      <AmountInput
        v-model="form.state.weight"
        :disabled="form.state.owned"
        :error-messages="form.errors('weight').length > 0 ? [''] : []"
        variant="outlined"
        hide-details
        class="w-[8rem] [&>div]:min-w-0"
      >
        <template #append>
          {{ t('rpc_node_form.weight_per_hundred') }}
        </template>
      </AmountInput>
    </div>

    <RuiSwitch
      v-model="form.state.owned"
      color="primary"
      class="mt-4"
      :label="t('rpc_node_form.owned')"
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.owned_hint')"
    />
    <RuiSwitch
      v-model="form.state.active"
      color="primary"
      class="mt-4"
      :label="t('rpc_node_form.active')"
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.active_hint')"
    />
  </div>
</template>
