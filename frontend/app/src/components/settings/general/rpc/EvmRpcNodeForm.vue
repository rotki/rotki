<script setup lang="ts">
import { between, required, requiredIf } from '@vuelidate/validators';
import { isEmpty, omit } from 'lodash-es';
import { type EvmRpcNode, getPlaceholderNode } from '@/types/settings/rpc';
import { toMessages } from '@/utils/validation';
import { ApiValidationError } from '@/types/api/errors';
import type { Blockchain } from '@rotki/common/lib/blockchain';

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

function getWeight(value?: string): number {
  if (!value)
    return 0;

  const parsedValue = parseInt(value);
  return Number.isNaN(parsedValue) ? 0 : parsedValue;
}

const weight = computed({
  get() {
    return get(state).weight.toString();
  },
  set(value?: string) {
    state.weight = getWeight(value);
  },
});

const rules = {
  name: { required },
  endpoint: { required: requiredIf(logicNot(isEtherscan)) },
  weight: { required, between: between(0, 100) },
};

const errorMessages = ref<Record<string, string[] | string>>({});

const { setValidation, setSubmitFunc } = useEvmRpcNodeForm(chain);

const v$ = setValidation(rules, state, {
  $autoDirty: true,
  $externalResults: errorMessages,
});

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

function updateState(selectedNode: EvmRpcNode): void {
  state.identifier = selectedNode.identifier;
  state.name = selectedNode.name;
  state.endpoint = selectedNode.endpoint;
  state.weight = selectedNode.weight;
  state.active = selectedNode.active;
  state.owned = selectedNode.owned;
}

onMounted(() => {
  updateState(get(value));
});

watch(value, (node) => {
  if (node === get(state))
    return;

  updateState(node);
});

watch(state, (state) => {
  emit('input', state);
});

const api = useEvmNodesApi(get(chain));
const { setMessage } = useMessageStore();

async function save() {
  const editing = get(editMode);
  try {
    const node = get(value);
    if (editing)
      return await api.editEvmNode(node);

    return await api.addEvmNode(omit(node, 'identifier'));
  }
  catch (error: any) {
    const chainProp = get(chainName);
    const errorTitle = editing
      ? t('evm_rpc_node_manager.edit_error.title', { chain: chainProp })
      : t('evm_rpc_node_manager.add_error.title', { chain: chainProp });

    if (error instanceof ApiValidationError) {
      const messages = error.errors;

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
          success: false,
        });
      }
    }
    else {
      setMessage({
        title: errorTitle,
        description: error.message,
        success: false,
      });
    }

    return false;
  }
}

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
      <RuiSlider
        v-model="state.weight"
        class="flex-1"
        :disabled="state.owned"
        :error-messages="toMessages(v$.weight)"
        :label="t('rpc_node_form.weight')"
        :min="0"
        :max="100"
        :hint="t('rpc_node_form.weight_hint', { weight: state.weight })"
        :step="1"
        show-thumb-label
        @blur="v$.weight.$touch()"
      />
      <AmountInput
        v-model="weight"
        :disabled="state.owned"
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
      v-model="state.owned"
      color="primary"
      class="mt-4"
      :label="t('rpc_node_form.owned')"
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.owned_hint')"
    />
    <RuiSwitch
      v-model="state.active"
      color="primary"
      class="mt-4"
      :label="t('rpc_node_form.active')"
      :disabled="isEtherscan"
      :hint="t('rpc_node_form.active_hint')"
    />
  </form>
</template>
