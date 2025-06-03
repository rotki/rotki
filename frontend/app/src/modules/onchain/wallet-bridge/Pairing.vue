<script setup lang="ts">
import type { SessionTypes } from '@walletconnect/types';
import type { TransactionRequest, TransactionResponse } from 'ethers';
import AppImage from '@/components/common/AppImage.vue';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { EIP155, ROTKI_DAPP_METADATA, useWalletStore } from '@/modules/onchain/use-wallet-store';
import { uniqueStrings } from '@/utils/data';
import { type IWalletKit, WalletKit, type WalletKitTypes } from '@reown/walletkit';
import { assert } from '@rotki/common';
import { get, set } from '@vueuse/core';
import { Core } from '@walletconnect/core';
import { formatJsonRpcError } from '@walletconnect/jsonrpc-utils';
import { buildApprovedNamespaces, getSdkError } from '@walletconnect/utils';
import { ref } from 'vue';

const props = defineProps<{
  connected?: boolean;
  address?: string;
  connectedChainId?: number;
  supportedChainIds: number[];
}>();

const COMPATIBLE_METHODS = [
  'eth_accounts',
  'net_version',
  'eth_chainId',
  'personal_sign',
  'eth_sign',
  'eth_signTypedData',
  'eth_signTypedData_v4',
  'eth_sendTransaction',
  'eth_blockNumber',
  'eth_getBalance',
  'eth_getCode',
  'eth_getTransactionCount',
  'eth_getStorageAt',
  'eth_getBlockByNumber',
  'eth_getBlockByHash',
  'eth_getTransactionByHash',
  'eth_getTransactionReceipt',
  'eth_estimateGas',
  'eth_call',
  'eth_getLogs',
  'eth_gasPrice',
  'wallet_switchEthereumChain',
  'wallet_sendCalls',
  'wallet_getCallsStatus',
  'wallet_showCallsStatus',
  'wallet_getCapabilities',
  'safe_setSettings',
];

const COMPATIBLE_EVENTS = ['chainChanged', 'accountsChanged'];

interface LogEntry {
  message: string;
  timestamp: string;
  type: 'info' | 'success' | 'error';
}

const { address, connected, connectedChainId, supportedChainIds } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });
const projectId = import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID as string;

const pairUri = ref('');
const logs = ref<LogEntry[]>([]);
const isConnecting = ref(false);
const walletKit = ref<IWalletKit>();
const activeSessions = ref<SessionTypes.Struct[]>([]);

const { getBrowserProvider, switchNetwork } = useWalletStore();
const { getChainIdFromNamespace, getEip155ChainId, getEvmChainNameFromChainId } = useWalletHelper();

function addLog(message: string, type: 'info' | 'success' | 'error' = 'info') {
  const timestamp = new Date().toLocaleTimeString();
  set(logs, [{ message, timestamp, type }, ...get(logs)]);
}

async function initializeWalletKit() {
  if (get(walletKit))
    return;

  const core = new Core({
    customStoragePrefix: 'ROTKI_WALLET_BRIDGE',
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
    await disconnectAllSessions();
    await kit.pair({ uri: pairUriVal });
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

function refreshActiveSessions() {
  set(activeSessions, getActiveSessions());
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
  const supportedChainIdsVal = get(supportedChainIds);

  if (!kit || !addressVal || !chainId)
    return;

  const chainIds = [...new Set([chainId, ...supportedChainIdsVal])];

  try {
    // ------- namespaces builder util ------------ //
    const approvedNamespaces = buildApprovedNamespaces({
      proposal: params,
      supportedNamespaces: {
        eip155: {
          accounts: chainIds.map(item => getEip155ChainId(`${item}:${addressVal}`)),
          chains: chainIds.map(item => getEip155ChainId(item)),
          events: COMPATIBLE_EVENTS,
          methods: COMPATIBLE_METHODS,
        },
      },
    });
    // ------- end namespaces builder util ------------ //

    await kit.approveSession({
      id,
      namespaces: approvedNamespaces,
    });

    refreshActiveSessions();
  }
  catch (error) {
    console.error(error);
  }
}

async function onSessionRequest(event: WalletKitTypes.SessionRequest) {
  const kit = get(walletKit);
  assert(kit);

  const { id, params, topic } = event;

  async function returnError(error: string) {
    assert(kit);
    const response = formatJsonRpcError(id, error);
    await kit.respondSessionRequest({ response, topic });
  }

  if (!get(connected)) {
    return returnError('Browser wallet signer is not connected');
  }

  const chainId = get(connectedChainId);
  const { chainId: chainIdWithNamespace } = params;
  const desiredChainId = getChainIdFromNamespace(chainIdWithNamespace);

  if (chainId !== desiredChainId) {
    try {
      await switchNetwork(BigInt(desiredChainId));
    }
    catch {
      return returnError('Failed to switch network');
    }
  }

  try {
    const request = params.request.params[0];
    const result = await triggerTransaction(request);
    const chainName = getEvmChainNameFromChainId(result.chainId);
    addLog(`Transaction initialized in ${chainName}: ${result.hash}`, 'success');
    const response = { id, jsonrpc: '2.0', result: result.hash };
    await kit.respondSessionRequest({ response, topic });
  }
  catch (error: any) {
    await returnError(error);
  }
}

// Set up event listeners as per documentation
function setupListeners() {
  const kit = get(walletKit);
  assert(kit);

  kit.on('session_proposal', onSessionProposal);
  kit.on('session_request', onSessionRequest);
  kit.on('session_delete', refreshActiveSessions);
}

function clearListeners() {
  const kit = get(walletKit);

  if (kit) {
    kit.off('session_proposal', onSessionProposal);
    kit.off('session_request', onSessionRequest);
    kit.off('session_delete', refreshActiveSessions);
  }
}

async function updateSession(session: SessionTypes.Struct, chainId: string, address: string) {
  const kit = get(walletKit);
  if (!kit) {
    return;
  }

  const currentEip155ChainIds = session.namespaces[EIP155]?.chains || [];
  const currentEip155Accounts = session.namespaces[EIP155]?.accounts || [];

  const newEip155ChainId = getEip155ChainId(chainId);
  const newEip155Account = `${newEip155ChainId}:${address}`;

  const namespaces: SessionTypes.Namespaces = {
    [EIP155]: {
      ...session.namespaces[EIP155],
      accounts: [newEip155Account, ...currentEip155Accounts].filter(uniqueStrings),
      chains: [newEip155ChainId, ...currentEip155ChainIds].filter(uniqueStrings),
    },
  };

  const { acknowledged } = await kit.updateSession({
    namespaces,
    topic: session.topic,
  });

  await acknowledged();

  // Switch to the new chain
  await chainChanged(session.topic, chainId);

  // Switch to the new Safe
  await accountsChanged(session.topic, chainId, address);
}

async function updateSessions(chainId?: string, address?: string) {
  if (!chainId || !address) {
    return;
  }

  for await (const session of get(activeSessions)) {
    await updateSession(session, chainId, address);
  }
}

async function disconnectSession(topic: string, skipRefresh = false) {
  const kit = get(walletKit);

  await kit!.disconnectSession({
    reason: getSdkError('USER_REJECTED'),
    topic,
  });

  if (!skipRefresh) {
    refreshActiveSessions();
  }
}

async function disconnectAllSessions() {
  for await (const session of get(activeSessions)) {
    await disconnectSession(session.topic, true);
  }
  refreshActiveSessions();
}

function clear() {
  clearListeners();
  disconnectAllSessions();
}

watch([walletKit, address, connectedChainId], ([walletKit, address, connectedChainId]) => {
  if (!walletKit || !address || !connectedChainId) {
    return;
  }

  refreshActiveSessions();
  updateSessions(connectedChainId.toString(), address);
});

watch(activeSessions, () => {
  updateSessions(get(connectedChainId)?.toString(), get(address));
});

onBeforeMount(initializeWalletKit);
onBeforeUnmount(clear);

const secondStep = '2';
</script>

<template>
  <div>
    <div
      class="py-4 border-t border-default"
      :class="{ 'opacity-30': !connected }"
    >
      <div class="flex gap-2">
        <div
          class="rounded-full bg-rui-primary text-white size-8 flex items-center justify-center font-bold"
        >
          {{ secondStep }}
        </div>
        <div class="mt-1 flex-1">
          <div class="mb-4 font-bold">
            {{ t('trade.bridge.link_session') }}
          </div>

          <div
            v-if="activeSessions.length === 0"
            class="space-y-4"
          >
            <RuiTextArea
              v-model="pairUri"
              :label="t('trade.bridge.label')"
              :placeholder="t('trade.bridge.placeholder')"
              :disabled="!connected"
              variant="outlined"
              color="primary"
              min-rows="6"
              clearable
              :hint="t('trade.bridge.hint')"
            />
            <div class="flex justify-end">
              <RuiButton
                :disabled="!pairUri.trim() || isConnecting || !connected"
                class="disabled:cursor-not-allowed"
                color="primary"
                @click="pair()"
              >
                {{ isConnecting ? t('trade.bridge.connecting') : t('trade.bridge.start_pairing') }}
              </RuiButton>
            </div>
          </div>

          <div v-else>
            <div class="border border-default rounded-md p-2">
              <div
                v-for="session in activeSessions"
                :key="session.topic"
                class="p-1 flex items-center justify-between"
              >
                <div class="flex items-center gap-3">
                  <AppImage
                    v-if="session.peer.metadata.icons[0]"
                    :src="session.peer.metadata.icons[0]"
                    size="24px"
                  />
                  {{ session.peer.metadata.name }}
                </div>
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
            <RuiAlert
              type="warning"
              class="mt-4"
            >
              {{ t('trade.bridge.warning') }}
            </RuiAlert>
          </div>
        </div>
      </div>
    </div>

    <div class="mt-4 pt-4 border-t border-default">
      <h3 class="text-xl font-semibold mb-4">
        {{ t('trade.bridge.connection_logs') }}
      </h3>
      <div class="border border-default rounded-md p-4 max-h-[300px] overflow-y-auto bg-rui-grey-50 dark:bg-rui-grey-900">
        <p
          v-for="(log, index) in logs"
          :key="index"
          class="mb-2 pb-2 border-b border-default font-mono last:mb-0 last:pb-0 last:border-0 text-sm break-words"
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
  </div>
</template>
