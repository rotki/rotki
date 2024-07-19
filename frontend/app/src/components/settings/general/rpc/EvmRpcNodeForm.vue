<script setup lang="ts">
import { between, required, requiredIf } from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
import useVuelidate from '@vuelidate/core';
import { toMessages } from '@/utils/validation';
import type { ValidationErrors } from '@/types/api/errors';
import type { EvmRpcNodeManageState } from '@/types/settings/rpc';

const props = defineProps<{
  modelValue: EvmRpcNodeManageState;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: EvmRpcNodeManageState): void;
}>();

const { t } = useI18n();

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const node = useSimplePropVModel(props, 'node', emit);
const owned = useRefPropVModel(node, 'owned');
const name = useRefPropVModel(node, 'name');
const endpoint = useRefPropVModel(node, 'endpoint');
const active = useRefPropVModel(node, 'active');
const numericWeight = useRefPropVModel(node, 'weight');

function getWeight(value?: string): number {
  if (!value)
    return 0;

  const parsedValue = parseInt(value);
  return Number.isNaN(parsedValue) ? 0 : parsedValue;
}

const weight = computed<string>({
  get() {
    return get(numericWeight).toString();
  },
  set(value?: string) {
    set(numericWeight, getWeight(value));
  },
});

const isEtherscan = computed<boolean>(() => {
  const rpcNode = get(node);
  return !rpcNode.endpoint && rpcNode.name.includes('etherscan');
});

const rules = {
  name: { required },
  endpoint: { required: requiredIf(logicNot(isEtherscan)) },
  weight: { required, between: between(0, 100) },
};

const v$ = useVuelidate(
  rules,
  {
    name,
    endpoint,
    weight,
    active,
    owned,
  },
  {
    $autoDirty: true,
    $externalResults: errors,
  },
);

watch(errors, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

defineExpose({
  validate: async () => await get(v$).$validate(),
});
</script>

<template>
  <form class="flex flex-col gap-2">
    <RuiTextField
      v-model="name"
      variant="outlined"
      color="primary"
      data-cy="node-name"
      :disabled="isEtherscan"
      :label="t('common.name')"
      :error-messages="toMessages(v$.name)"
      @blur="v$.name.$touch()"
    />
    <RuiTextField
      v-model="endpoint"
      variant="outlined"
      color="primary"
      data-cy="node-endpoint"
      :disabled="isEtherscan"
      :error-messages="toMessages(v$.endpoint)"
      :label="t('rpc_node_form.endpoint')"
      @blur="v$.endpoint.$touch()"
    />

    <div class="flex items-center gap-4">
      <RuiSlider
        v-model="numericWeight"
        class="flex-1"
        :disabled="owned"
        :error-messages="toMessages(v$.weight)"
        :label="t('rpc_node_form.weight')"
        :min="0"
        :max="100"
        :hint="t('rpc_node_form.weight_hint', { weight })"
        :step="1"
        show-thumb-label
        @blur="v$.weight.$touch()"
      />
      <AmountInput
        v-model="weight"
        :disabled="owned"
        :error-messages="toMessages(v$.weight).length > 0 ? [''] : []"
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
      v-model="owned"
      color="primary"
      class="mt-4"
      :label="t('rpc_node_form.owned')"
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.owned_hint')"
    />
    <RuiSwitch
      v-model="active"
      color="primary"
      class="mt-4"
      :label="t('rpc_node_form.active')"
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.active_hint')"
    />
  </form>
</template>
