<script setup lang="ts">
import { between, required, requiredIf } from '@vuelidate/validators';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { isEmpty, omit } from 'lodash-es';
import { type EvmRpcNode, getPlaceholderNode } from '@/types/settings/rpc';
import { toMessages } from '@/utils/validation';
import { ApiValidationError } from '@/types/api/errors';

const props = defineProps<{
  value: EvmRpcNode;
  chain: Blockchain;
  chainName: string;
  isEtherscan: boolean;
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', value: EvmRpcNode): void;
}>();

const { t } = useI18n();

const { chain, chainName, value, isEtherscan, editMode } = toRefs(props);
const state = reactive<EvmRpcNode>(getPlaceholderNode(get(chain)));

const rules = {
  name: { required },
  endpoint: { required: requiredIf(logicNot(isEtherscan)) },
  weight: { required, between: between(0, 100) }
};

const errorMessages = ref<Record<string, string[] | string>>({});

const { setValidation, setSubmitFunc } = useEvmRpcNodeForm(chain);

const v$ = setValidation(rules, state, {
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
});

const api = useEvmNodesApi(get(chain));
const { setMessage } = useMessageStore();

const save = async () => {
  const editing = get(editMode);
  try {
    const node = get(value);
    if (editing) {
      return await api.editEvmNode(node);
    }
    return await api.addEvmNode(omit(node, 'identifier'));
  } catch (e: any) {
    const chainProp = get(chainName);
    const errorTitle = editing
      ? t('evm_rpc_node_manager.edit_error.title', { chain: chainProp })
      : t('evm_rpc_node_manager.add_error.title', { chain: chainProp });

    if (e instanceof ApiValidationError) {
      const messages = e.errors;

      set(errorMessages, messages);

      const keys = Object.keys(messages);
      const knownKeys = Object.keys(get(value));
      const unknownKeys = keys.filter(key => !knownKeys.includes(key));

      if (unknownKeys.length > 0) {
        setMessage({
          title: errorTitle,
          description: unknownKeys
            .map(key => `${key}: ${messages[key]}`)
            .join(', '),
          success: false
        });
      }
    } else {
      setMessage({
        title: errorTitle,
        description: e.message,
        success: false
      });
    }

    return false;
  }
};

setSubmitFunc(save);
</script>

<template>
  <form class="flex flex-col gap-2">
    <RuiTextField
      v-model="state.name"
      variant="outlined"
      color="primary"
      data-cy="node-name"
      :disabled="isEtherscan"
      :label="t('common.name')"
      :error-messages="toMessages(v$.name)"
      @blur="v$.name.$touch()"
    />
    <RuiTextField
      v-model="state.endpoint"
      variant="outlined"
      color="primary"
      data-cy="node-endpoint"
      :disabled="isEtherscan"
      :error-messages="toMessages(v$.endpoint)"
      :label="t('rpc_node_form.endpoint')"
      @blur="v$.endpoint.$touch()"
    />

    <div class="flex items-center gap-4">
      <VSlider
        :value="state.weight"
        :disabled="state.owned"
        :error-messages="toMessages(v$.weight)"
        :label="t('rpc_node_form.weight')"
        min="0"
        max="100"
        persistent-hint
        :hint="t('rpc_node_form.weight_hint', { weight: state.weight })"
        step="1"
        class="grow"
        thumb-label
        @change="state.weight = $event"
        @blur="v$.weight.$touch()"
      />
      <AmountInput
        :disabled="state.owned"
        :value="state.weight.toString()"
        :error-messages="toMessages(v$.weight).length > 0 ? [''] : []"
        outlined
        hide-details
        class="shrink ml-2 w-[8rem]"
        @input="state.weight = $event"
      />
      {{ t('rpc_node_form.weight_per_hundred') }}
    </div>

    <VSwitch
      v-model="state.owned"
      :label="t('rpc_node_form.owned')"
      persistent-hint
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.owned_hint')"
    />
    <VSwitch
      v-model="state.active"
      :label="t('rpc_node_form.active')"
      persistent-hint
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.active_hint')"
    />
  </form>
</template>
