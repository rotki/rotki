<script setup lang="ts">
import type { RpcProviderCandidate } from '@/modules/settings/general/rpc/providers/rpc-provider-plan';
import type { BlockchainRpcNode, BlockchainRpcNodeManageState } from '@/modules/settings/types/rpc';
import { assert, Blockchain } from '@rotki/common';
import { omit } from 'es-toolkit';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { isBlockchain } from '@/modules/core/common/chains';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useEvmNodesApi } from '@/modules/settings/api/use-evm-nodes-api';
import BlockchainRpcNodeForm from '@/modules/settings/general/rpc/BlockchainRpcNodeForm.vue';
import RpcProviderFanOutOffer from '@/modules/settings/general/rpc/providers/RpcProviderFanOutOffer.vue';
import RpcProviderRunResults from '@/modules/settings/general/rpc/providers/RpcProviderRunResults.vue';
import { useRpcNodeFanOut } from '@/modules/settings/general/rpc/providers/use-rpc-node-fan-out';
import { RPC_SETUP_STATUS, useRpcProviderSetup } from '@/modules/settings/general/rpc/providers/use-rpc-provider-setup';
import BigDialog, { type BigDialogLayout } from '@/modules/shell/components/dialogs/BigDialog.vue';

const model = defineModel<BlockchainRpcNodeManageState | undefined>({ required: true });

/** The chains that hold a node list, which is what a provider key can be fanned out over. */
const { chains } = defineProps<{
  chains: string[];
}>();

const emit = defineEmits<{
  complete: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const errorMessages = ref<ValidationErrors>({});
const submitting = ref<boolean>(false);
const form = useTemplateRef<InstanceType<typeof BlockchainRpcNodeForm>>('form');
const stateUpdated = ref(false);
/** Whether the dialog is still the form, or already reporting what the other chains did. */
const phase = ref<'form' | 'results'>('form');

const { useChainName } = useSupportedChains();

const chain = computed<Blockchain>(() => {
  const blockchain = get(model)?.node.blockchain;
  if (!blockchain || !isBlockchain(blockchain))
    return Blockchain.ETH;

  return blockchain;
});

const chainName = useChainName(() => get(model)?.node.blockchain);

const dialogTitle = computed(() => {
  const state = get(model);
  if (state?.mode === 'edit') {
    return t('evm_rpc_node_manager.edit_dialog.title', {
      chain: get(chainName),
    });
  }
  return t('evm_rpc_node_manager.add_dialog.title', { chain: get(chainName) });
});

const api = useEvmNodesApi(chain);
const { setMessage } = useMessageStore();

const {
  candidates,
  chosen,
  credential,
  enablementNote,
  modelEnabled: fanOutEnabled,
  preparing,
  provider,
  reset: resetFanOut,
  selected: selectedChains,
  toggle: toggleChain,
  unreadableNames,
  unsupportedNames,
} = useRpcNodeFanOut(
  () => get(model)?.node.endpoint ?? '',
  () => get(model)?.node.name ?? '',
  chain,
  () => chains,
);
const { reset: resetRun, retry, rows, running, run, stop, summary } = useRpcProviderSetup();

/** The offer only makes sense while adding: an edit is one node on one chain by definition. */
const offered = computed<boolean>(() => get(model)?.mode === 'add' && get(provider) !== undefined);

/** The results are a short list, so they take the height they need instead of the form's. */
const layout = computed<BigDialogLayout | undefined>(() =>
  get(phase) === 'results' ? { autoHeight: true, maxWidth: '640px' } : undefined);

const action = computed(() => {
  if (get(phase) === 'form')
    return { primary: t('common.actions.save') };

  return {
    hidden: get(running) || get(summary).failed === 0,
    primary: t('rpc_provider_setup.actions.retry'),
    secondary: t('rpc_provider_setup.actions.close'),
  };
});

function resetForm(): void {
  stop();
  resetRun();
  resetFanOut();
  set(phase, 'form');
  set(model, undefined);
}

/**
 * Walks the other chains, keeping the dialog open on what each one did.
 *
 * @remarks
 * The node the form added is not among them: it is already in the list the manager reloads.
 */
async function fanOutToOtherChains(candidates: RpcProviderCandidate[], walk: () => Promise<void>): Promise<void> {
  if (candidates.length === 0) {
    resetForm();
    return;
  }

  set(phase, 'results');
  await walk();
  emit('complete');
}

async function save(): Promise<void> {
  if (!get(form)?.validate())
    return;

  const state = get(model);
  assert(state);

  const editing = state.mode === 'edit';
  const node = state.node;
  let saved = false;

  set(submitting, true);
  try {
    if (editing)
      await api.editEvmNode(node);
    else await api.addEvmNode(omit(node, ['identifier']));
    saved = true;
    emit('complete');
  }
  catch (error: unknown) {
    const chainProp = get(chainName);
    const errorTitle = editing
      ? t('evm_rpc_node_manager.edit_error.title', { chain: chainProp })
      : t('evm_rpc_node_manager.add_error.title', { chain: chainProp });

    if (error instanceof ApiValidationError) {
      const messages = error.errors;

      set(errorMessages, messages);

      const keys = Object.keys(messages);
      const formKeys: string[] = ['name', 'endpoint', 'weight', 'owned', 'active'] satisfies (keyof BlockchainRpcNode)[];
      const nodeKeys = Object.keys(node);
      const nonFormKeys = keys.filter(key => !formKeys.includes(key) && nodeKeys.includes(key));

      if (nonFormKeys.length > 0) {
        setMessage({
          description: nonFormKeys.map(key => `${key}: ${messages[key]}`).join(', '),
          success: false,
          title: errorTitle,
        });
      }
    }
    else {
      setMessage({
        description: getErrorMessage(error),
        success: false,
        title: errorTitle,
      });
    }
  }
  finally {
    set(submitting, false);
  }

  if (!saved)
    return;

  if (get(fanOutEnabled)) {
    const candidates = get(chosen);
    await fanOutToOtherChains(candidates, async () => run(candidates));
  }
  else {
    resetForm();
  }
}

async function confirm(): Promise<void> {
  if (get(phase) === 'form') {
    await save();
    return;
  }

  const failed = get(rows)
    .filter(row => row.status === RPC_SETUP_STATUS.FAILED)
    .map(row => row.chain);
  const failedCandidates = get(candidates).filter(candidate => failed.includes(candidate.chain));
  await fanOutToOtherChains(failedCandidates, async () => retry(failedCandidates));
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :action="action"
    :prompt-on-close="phase === 'form' && stateUpdated"
    :layout="layout"
    :loading="submitting"
    @confirm="confirm()"
    @cancel="resetForm()"
  >
    <RpcProviderRunResults
      v-if="phase === 'results'"
      :rows="rows"
      :running="running"
      :summary="summary"
      :enablement="enablementNote"
      :credential="credential"
    />
    <template v-else>
      <RpcProviderFanOutOffer
        v-if="offered && provider"
        v-model="fanOutEnabled"
        :provider="provider.name"
        :candidates="candidates"
        :selected="selectedChains"
        :preparing="preparing"
        :unsupported="unsupportedNames"
        :unreadable="unreadableNames"
        :enablement="enablementNote"
        @toggle="toggleChain($event.chain, $event.checked)"
      />
      <BlockchainRpcNodeForm
        v-if="model"
        ref="form"
        v-model="model"
        v-model:error-messages="errorMessages"
        v-model:state-updated="stateUpdated"
        :restricted="fanOutEnabled"
      />
    </template>
  </BigDialog>
</template>
