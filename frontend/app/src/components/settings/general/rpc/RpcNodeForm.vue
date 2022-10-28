<template>
  <form class="pt-2">
    <v-text-field
      v-model="state.name"
      outlined
      data-cy="node-name"
      :disabled="isEtherscan"
      :label="tc('common.name')"
      :error-messages="v$.name.$errors.map(e => e.$message)"
      @blur="v$.name.$touch()"
    />
    <v-text-field
      v-model="state.endpoint"
      outlined
      data-cy="node-endpoint"
      :disabled="isEtherscan"
      :error-messages="v$.endpoint.$errors.map(e => e.$message)"
      :label="tc('rpc_node_form.endpoint')"
      @blur="v$.endpoint.$touch()"
    />

    <v-row align="center">
      <v-col>
        <v-slider
          :value="state.weight"
          :disabled="state.owned"
          :error-messages="v$.weight.$errors.map(e => e.$message)"
          :label="tc('rpc_node_form.weight')"
          min="0"
          max="100"
          persistent-hint
          :hint="tc('rpc_node_form.weight_hint', 0, { weight: state.weight })"
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
          :error-messages="v$.weight.$errors.map(() => '')"
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
      :label="tc('rpc_node_form.owned')"
      persistent-hint
      :disabled="isEtherscan"
      :hint="tc('rpc_node_form.owned_hint')"
    />
    <v-switch
      v-model="state.active"
      :label="tc('rpc_node_form.active')"
      persistent-hint
      :disabled="isEtherscan"
      :hint="tc('rpc_node_form.active_hint')"
    />
  </form>
</template>

<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, required, requiredIf } from '@vuelidate/validators';
import { PropType } from 'vue';
import { EthereumRpcNode, getPlaceholderNode } from '@/types/settings';

const { t, tc } = useI18n();

const props = defineProps({
  value: {
    required: true,
    type: Object as PropType<EthereumRpcNode>
  },
  isEtherscan: {
    required: true,
    type: Boolean
  },
  errorMessages: {
    required: false,
    type: Object as PropType<Record<string, string | string[]>>,
    default: null
  }
});

const emit = defineEmits(['input', 'update:valid']);
const { value, errorMessages } = toRefs(props);
const state = reactive<EthereumRpcNode>(getPlaceholderNode());
const rules = {
  name: { required },
  endpoint: { required: requiredIf(() => state.name !== 'etherscan') },
  weight: { required, between: between(0, 100) }
};

const v$ = useVuelidate(rules, state, { $externalResults: errorMessages });

const updateState = (selectedNode: EthereumRpcNode): void => {
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
<style lang="scss" module>
.input {
  width: 100px;
}
</style>
