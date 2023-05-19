<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, required, requiredIf } from '@vuelidate/validators';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import isEmpty from 'lodash/isEmpty';
import { type EvmRpcNode, getPlaceholderNode } from '@/types/settings';
import { toMessages } from '@/utils/validation';

const { t } = useI18n();

const props = withDefaults(
  defineProps<{
    value: EvmRpcNode;
    chain: Blockchain;
    isEtherscan: boolean;
    errorMessages?: Record<string, string | string[]>;
  }>(),
  {
    errorMessages: () => ({})
  }
);

const emit = defineEmits<{
  (e: 'input', value: EvmRpcNode): void;
  (e: 'update:valid', valid: boolean): void;
}>();

const { chain, value, errorMessages, isEtherscan } = toRefs(props);
const state = reactive<EvmRpcNode>(getPlaceholderNode(get(chain)));
const rules = {
  name: { required },
  endpoint: { required: requiredIf(logicNot(isEtherscan)) },
  weight: { required, between: between(0, 100) }
};

const v$ = useVuelidate(rules, state, {
  $autoDirty: true,
  $externalResults: errorMessages
});

watch(errorMessages, errors => {
  if (!isEmpty(errors)) {
    get(v$).$validate();
  }
});

const updateState = (selectedNode: EvmRpcNode): void => {
  state.identifier = selectedNode.identifier;
  state.name = selectedNode.name;
  state.endpoint = selectedNode.endpoint;
  state.weight = selectedNode.weight;
  state.active = selectedNode.active;
  state.owned = selectedNode.owned;
};

onMounted(() => {
  updateState(get(value));
});

watch(value, node => {
  if (node === get(state)) {
    return;
  }
  updateState(node);
});

watch(state, state => {
  emit('input', state);
  emit('update:valid', !get(v$).$invalid);
});
</script>

<template>
  <form class="pt-2">
    <v-text-field
      v-model="state.name"
      outlined
      data-cy="node-name"
      :disabled="isEtherscan"
      :label="t('common.name')"
      :error-messages="toMessages(v$.name)"
      @blur="v$.name.$touch()"
    />
    <v-text-field
      v-model="state.endpoint"
      outlined
      data-cy="node-endpoint"
      :disabled="isEtherscan"
      :error-messages="toMessages(v$.endpoint)"
      :label="t('rpc_node_form.endpoint')"
      @blur="v$.endpoint.$touch()"
    />

    <v-row align="center">
      <v-col>
        <v-slider
          :value="state.weight"
          :disabled="state.owned"
          :error-messages="toMessages(v$.weight)"
          :label="t('rpc_node_form.weight')"
          min="0"
          max="100"
          persistent-hint
          :hint="t('rpc_node_form.weight_hint', { weight: state.weight })"
          step="1"
          thumb-label
          @change="state.weight = $event"
          @blur="v$.weight.$touch()"
        />
      </v-col>
      <v-col cols="auto">
        <amount-input
          :disabled="state.owned"
          :value="state.weight.toString()"
          :error-messages="toMessages(v$.weight).length > 0 ? [''] : []"
          outlined
          hide-details
          :class="$style.input"
          @input="state.weight = $event"
        />
      </v-col>
      <v-col cols="auto" class="pl-0">
        {{ t('rpc_node_form.weight_per_hundred') }}
      </v-col>
    </v-row>

    <v-switch
      v-model="state.owned"
      :label="t('rpc_node_form.owned')"
      persistent-hint
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.owned_hint')"
    />
    <v-switch
      v-model="state.active"
      :label="t('rpc_node_form.active')"
      persistent-hint
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.active_hint')"
    />
  </form>
</template>

<style lang="scss" module>
.input {
  width: 100px;
}
</style>
