<script setup lang="ts">
import type { SessionTypes } from '@walletconnect/types';
import type { TransactionRequest, TransactionResponse } from 'ethers';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { EIP155, ROTKI_DAPP_METADATA, useWalletStore } from '@/modules/onchain/use-wallet-store';
import { type IWalletKit, WalletKit, type WalletKitTypes } from '@reown/walletkit';
import { assert } from '@rotki/common';
import { get, set } from '@vueuse/core';
import { Core } from '@walletconnect/core';
import { formatJsonRpcError } from '@walletconnect/jsonrpc-utils';
import { buildApprovedNamespaces, getSdkError } from '@walletconnect/utils';
import { ref } from 'vue';

interface LogEntry {
  message: string;
  timestamp: string;
  type: 'info' | 'success' | 'error';
}

const props = defineProps<{
  address: string;
  connectedChainId: number;
}>();

const { address, connectedChainId } = toRefs(props);

const { t } = useI18n();
const projectId = import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID as string;

const pairUri = ref('');
const logs = ref<LogEntry[]>([]);
const isConnecting = ref(false);
const walletKit = ref<IWalletKit>();
const activeSessions = ref<SessionTypes.Struct[]>([]);

const { getBrowserProvider } = useWalletStore();
const { getEip155ChainId, getEvmChainNameFromChainId } = useWalletHelper();

function addLog(message: string, type: 'info' | 'success' | 'error' = 'info') {
  const timestamp = new Date().toLocaleTimeString();
  set(logs, [{ message, timestamp, type }, ...get(logs)]);
}

async function initializeWalletKit() {
  if (get(walletKit))
    return;

  const core = new Core({
    projectId,
  });

  try {
    set(walletKit, await WalletKit.init({
      core,
      metadata: ROTKI_DAPP_METADATA,
    }));
    setupListeners();

    addLog('WalletKit initialized successfully', 'success');
  }
  catch (error) {
    addLog(`Failed to initialize WalletKit: ${(error as Error).message}`, 'error');
  }
}

async function pair() {
  const pairUriVal = get(pairUri).trim();
  if (!pairUriVal) {
    addLog('Please enter a valid Pair URI', 'error');
    return;
  }

  set(isConnecting, true);

  try {
    if (!isDefined(walletKit)) {
      throw new Error('WalletKit not initialized');
    }
    const kit = get(walletKit);

    // Connect using the URI
    await kit.core.pairing.pair({ uri: pairUriVal });
    addLog('Successfully paired with the Electron app, you can now perform transactions in the app.', 'success');

    set(pairUri, '');
  }
  catch (error) {
    addLog(`Connection failed: ${(error as Error).message}`, 'error');
  }
  finally {
    set(isConnecting, false);
  }
}

function getActiveSessions(): SessionTypes.Struct[] {
  const kit = get(walletKit);
  if (!kit)
    return [];

  const sessionsMap = kit.getActiveSessions() || {};
  return Object.values(sessionsMap);
}

async function chainChanged(topic: string, chainId: string) {
  const kit = get(walletKit);
  if (!isDefined(kit)) {
    return;
  }

  const eipChainId = getEip155ChainId(chainId);

  return kit.emitSessionEvent({
    chainId: eipChainId,
    event: {
      data: Number(chainId),
      name: 'chainChanged',
    },
    topic,
  });
}

async function accountsChanged(topic: string, chainId: string, address: string) {
  const kit = get(walletKit);
  if (!isDefined(kit)) {
    return;
  }

  const eipChainId = getEip155ChainId(chainId);

  return kit.emitSessionEvent({
    chainId: eipChainId,
    event: {
      data: [address],
      name: 'accountsChanged',
    },
    topic,
  });
}

async function triggerTransaction(request: TransactionRequest): Promise<TransactionResponse> {
  try {
    const browserProvider = getBrowserProvider();
    const signer = await browserProvider.getSigner();

    return await signer.sendTransaction(request);
  }
  catch (error) {
    console.error(error);
    throw error;
  }
}

async function onSessionProposal({ id, params }: WalletKitTypes.SessionProposal) {
  const kit = get(walletKit);
  const addressVal = get(address);
  const chainId = get(connectedChainId);

  if (!kit || !addressVal)
    return;

  const chainIds = [chainId];
  try {
    // ------- namespaces builder util ------------ //
    const approvedNamespaces = buildApprovedNamespaces({
      proposal: params,
      supportedNamespaces: {
        eip155: {
          accounts: chainIds.map(item => getEip155ChainId(`${item}:${addressVal}`)),
          chains: chainIds.map(item => getEip155ChainId(item)),
          events: ['accountsChanged', 'chainChanged'],
          methods: ['eth_sendTransaction', 'eth_requestAccounts', 'personal_sign'],
        },
      },
    });
    // ------- end namespaces builder util ------------ //

    await kit.approveSession({
      id,
      namespaces: approvedNamespaces,
    });

    set(activeSessions, getActiveSessions());
  }
  catch (error) {
    console.error(error);
  }
}

async function onSessionRequest(event: WalletKitTypes.SessionRequest) {
  const kit = get(walletKit);
  assert(kit);

  const { id, params, topic } = event;
  try {
    const request = params.request.params[0];
    const result = await triggerTransaction(request);
    const chainName = getEvmChainNameFromChainId(result.chainId);
    addLog(`Transaction initialized in ${chainName}: ${result.hash}`, 'success');
    const response = { id, jsonrpc: '2.0', result: result.hash };
    await kit.respondSessionRequest({ response, topic });
  }
  catch (error: any) {
    const response = formatJsonRpcError(id, error);
    await kit.respondSessionRequest({ response, topic });
  }
}

// Set up event listeners as per documentation
function setupListeners() {
  const kit = get(walletKit);
  assert(kit);

  kit.on('session_proposal', onSessionProposal);
  kit.on('session_request', onSessionRequest);
}

async function updateSession(session: SessionTypes.Struct, chainId: string, address: string) {
  const kit = get(walletKit);

  const currentEip155ChainIds = session.namespaces[EIP155]?.chains || [];
  const currentEip155Accounts = session.namespaces[EIP155]?.accounts || [];

  const newEip155ChainId = getEip155ChainId(chainId);
  const newEip155Account = `${newEip155ChainId}:${address}`;

  const isNewSession = !currentEip155Accounts.includes(newEip155Account);

  if (isNewSession) {
    const namespaces: SessionTypes.Namespaces = {
      [EIP155]: {
        ...session.namespaces[EIP155],
        accounts: [newEip155Account, ...currentEip155Accounts],
        chains: [newEip155ChainId, ...currentEip155ChainIds],
      },
    };

    await kit!.updateSession({
      namespaces,
      topic: session.topic,
    });
  }

  // Switch to the new chain
  await chainChanged(session.topic, chainId);

  // Switch to the new Safe
  await accountsChanged(session.topic, chainId, address);
}

async function updateSessions(chainId: string, address: string) {
  for await (const session of get(activeSessions)) {
    await updateSession(session, chainId, address);
  }
}

async function disconnectSession(topic: string) {
  const kit = get(walletKit);

  await kit!.disconnectSession({
    reason: getSdkError('USER_REJECTED'),
    topic,
  });

  set(activeSessions, getActiveSessions());
}

watch([walletKit, address, connectedChainId], ([walletKit, address, connectedChainId]) => {
  if (walletKit && address) {
    set(activeSessions, getActiveSessions());
    updateSessions(connectedChainId.toString(), address);
  }
});

watch(activeSessions, () => {
  updateSessions(get(connectedChainId).toString(), get(address));
});

onBeforeMount(initializeWalletKit);
</script>

<template>
  <div>
    <div class="space-y-4">
      <label
        for="pairUri"
        class="block font-semibold"
      >
        {{ t('trade.bridge.subtitle') }}
      </label>
      <RuiTextArea
        v-model="pairUri"
        :label="t('trade.bridge.label')"
        variant="outlined"
        color="primary"
        min-rows="6"
        clearable
        :hint="t('trade.bridge.hint')"
      />

      <RuiButton
        :disabled="!pairUri.trim() || isConnecting"
        class="disabled:cursor-not-allowed"
        color="success"
        @click="pair()"
      >
        {{ isConnecting ? t('trade.bridge.connecting') : t('trade.bridge.start_pairing') }}
      </RuiButton>
    </div>

    <div class="mt-4 pt-4 border-t border-default">
      <h3 class="text-xl font-semibold mb-4">
        {{ t('trade.bridge.connection_logs') }}
      </h3>
      <div class="border border-default rounded-md p-4 max-h-[300px] overflow-y-auto bg-rui-grey-50 dark:bg-rui-grey-900">
        <p
          v-for="(log, index) in logs"
          :key="index"
          class="mb-2 pb-2 border-b border-default font-mono last:mb-0 last:pb-0 last:border-0 text-sm"
          :class="{
            'text-rui-primary': log.type === 'info',
            'text-rui-success': log.type === 'success',
            'text-rui-error': log.type === 'error',
          }"
        >
          <span class="text-gray-500 mr-1">{{ log.timestamp }}</span>
          {{ log.message }}
        </p>
      </div>
    </div>
    <div>
      <div
        v-for="session in activeSessions"
        :key="session.topic"
        class="py-3 flex items-center justify-between border-b border-default"
      >
        {{ session.peer.metadata.name }}
        <RuiButton
          variant="text"
          color="error"
          size="sm"
          @click="disconnectSession(session.topic)"
        >
          {{ t('trade.bridge.disconnect_session') }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
