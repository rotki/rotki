<template>
  <form class="pt-2">
    <v-text-field
      v-model="state.name"
      outlined
      :disabled="edit"
      :label="$tc('rpc_node_form.name')"
      :error-messages="v$.name.$errors.map(e => e.$message)"
      @blur="v$.name.$touch()"
    />
    <v-text-field
      v-model="state.endpoint"
      outlined
      :error-messages="v$.endpoint.$errors.map(e => e.$message)"
      :label="$tc('rpc_node_form.endpoint')"
      @blur="v$.endpoint.$touch()"
    />

    <v-slider
      v-model.number="state.weight"
      :disabled="state.owned"
      :error-messages="v$.weight.$errors.map(e => e.$message)"
      :label="$tc('rpc_node_form.weight')"
      min="0"
      max="100"
      persistent-hint
      :hint="$tc('rpc_node_form.weight_hint', 0, { weight: state.weight })"
      step="1"
      thumb-label
      @blur="v$.weight.$touch()"
    />

    <v-switch
      v-model="state.owned"
      :label="$tc('rpc_node_form.owned')"
      persistent-hint
      :hint="$tc('rpc_node_form.owned_hint')"
    />
    <v-switch
      v-model="state.active"
      :label="$tc('rpc_node_form.active')"
      persistent-hint
      :hint="$tc('rpc_node_form.active_hint')"
    />
  </form>
</template>

<script lang="ts">
import {
  defineComponent,
  onMounted,
  PropType,
  reactive,
  toRefs,
  watch
} from '@vue/composition-api';
import useVuelidate from '@vuelidate/core';
import { between, required } from '@vuelidate/validators';
import { get } from '@vueuse/core';
import { EthereumRpcNode, getPlaceholderNode } from '@/types/settings';

export default defineComponent({
  name: 'RpcNodeForm',
  props: {
    value: {
      required: true,
      type: Object as PropType<EthereumRpcNode>
    },
    edit: {
      required: true,
      type: Boolean
    },
    errorMessages: {
      required: false,
      type: Object as PropType<Record<string, string | string[]>>,
      default: null
    }
  },
  emits: ['input', 'update:valid'],
  setup(props, { emit }) {
    const { value, errorMessages } = toRefs(props);
    const state = reactive<EthereumRpcNode>(getPlaceholderNode());
    const rules = {
      name: { required },
      endpoint: { required },
      weight: { required, between: between(0, 100) }
    };

    const v$ = useVuelidate(rules, state, { $externalResults: errorMessages });

    const updateState = (selectedNode: EthereumRpcNode): void => {
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

    return {
      state,
      v$
    };
  }
});
</script>
