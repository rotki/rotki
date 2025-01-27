<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { get, set } from '@vueuse/core';
import { WalletKit, type WalletKitTypes } from '@reown/walletkit';
import { buildApprovedNamespaces, getSdkError } from '@walletconnect/utils';
import { Core } from '@walletconnect/core';
import { baseSepolia } from '@reown/appkit/networks';
import type { SessionTypes } from '@walletconnect/types';
import type Web3WalletType from '@reown/walletkit';

const props = defineProps<{
  address: string;
  metadata: any;
}>();

const emit = defineEmits<{
  (e: 'send-eth', event: { address: string; value: string }): Promise<boolean>;
}>();

const { address } = toRefs(props);

// Constants
const PROJECT_ID = 'eca1bd3842e084bfc8ef309b6eb584db';
const EIP155 = 'eip155' as const;

/* WalletConnect Core Setup */
const core = new Core({
  projectId: PROJECT_ID,
});

interface LogEntry {
  message: string;
  timestamp: string;
  type: 'info' | 'success' | 'error';
}

// State
const pairUri = ref('');
const logs = ref<LogEntry[]>([]);
const isConnecting = ref(false);
const walletKit = ref<Web3WalletType | null>(null);
const activeSessions = ref<SessionTypes.Struct[]>([]);

// Logging utility
function addLog(message: string, type: 'info' | 'success' | 'error' = 'info') {
  const timestamp = new Date().toLocaleTimeString();
  set(logs, [{ message, timestamp, type }, ...get(logs)]);
}

// Initialize WalletKit following official docs
async function initializeWalletKit() {
  try {
    set(walletKit, await WalletKit.init({
      core,
      metadata: props.metadata,
    }));

    addLog('WalletKit initialized successfully', 'success');
  }
  catch (error) {
    addLog(`Failed to initialize WalletKit: ${(error as Error).message}`, 'error');
  }
}

// Connect with WalletKit
async function connectWithWalletKit() {
  if (!get(pairUri).trim()) {
    addLog('Please enter a valid Pair URI', 'error');
    return;
  }

  set(isConnecting, true);

  try {
    const kit = get(walletKit);
    if (!kit) {
      await initializeWalletKit();
    }

    if (!kit) {
      throw new Error('WalletKit not initialized');
    }

    // Connect using the URI
    const uri = get(pairUri).trim();
    await kit.core.pairing.pair({ uri });
    addLog('Successfully paired with the Electron app', 'success');

    set(pairUri, ''); // Clear the input after successful pairing
  }
  catch (error) {
    addLog(`Connection failed: ${(error as Error).message}`, 'error');
  }
  finally {
    set(isConnecting, false);
  }
}

async function onSessionProposal({ id, params }: WalletKitTypes.SessionProposal) {
  const kit = get(walletKit);
  const addressVal = get(address);
  if (!kit || !addressVal)
    return;

  try {
    // ------- namespaces builder util ------------ //
    const approvedNamespaces = buildApprovedNamespaces({
      proposal: params,
      supportedNamespaces: {
        eip155: {
          accounts: [
            getEip155ChainId(`${baseSepolia.id}:${addressVal}`),
          ],
          chains: [getEip155ChainId(`${baseSepolia.id}`)],
          events: ['accountsChanged', 'chainChanged'],
          methods: ['eth_sendTransaction', 'personal_sign'],
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

function getActiveSessions(): SessionTypes.Struct[] {
  const kit = get(walletKit);
  if (!kit)
    return [];

  const sessionsMap = kit.getActiveSessions() || {};
  return Object.values(sessionsMap);
}

function getEip155ChainId(chainId: string): string {
  return `${EIP155}:${chainId}`;
}

async function chainChanged(topic: string, chainId: string) {
  const kit = get(walletKit);

  const eipChainId = getEip155ChainId(chainId);

  return kit?.emitSessionEvent({
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

  const eipChainId = getEip155ChainId(chainId);

  return kit?.emitSessionEvent({
    chainId: eipChainId,
    event: {
      data: [address],
      name: 'accountsChanged',
    },
    topic,
  });
}

// Set up event listeners as per documentation
function setupListeners() {
  const kit = get(walletKit);
  if (!kit)
    return;

  console.log('test');
  kit.on('session_proposal', onSessionProposal);

  kit.on('session_request', async (event) => {
    console.log(event.params.request);
    const { to, value } = event.params.request.params[0];
    console.log(event, to, value);
    const success = await emit('send-eth', {
      address: to,
      value,
    });
  });
}

async function updateSession(session: SessionTypes.Struct, chainId: string, address: string) {
  const kit = get(walletKit);

  const currentEip155ChainIds = session.namespaces[EIP155]?.chains || [];
  const currentEip155Accounts = session.namespaces[EIP155]?.accounts || [];

  const newEip155ChainId = getEip155ChainId(chainId);
  const newEip155Account = `${newEip155ChainId}:${address}`;

  const isNewSessionSafe = !currentEip155Accounts.includes(newEip155Account);

  // Add new Safe to the session namespace
  if (isNewSessionSafe) {
    const namespaces: SessionTypes.Namespaces = {
      [EIP155]: {
        ...session.namespaces[EIP155],
        accounts: [newEip155Account, ...currentEip155Accounts],
        chains: currentEip155ChainIds,
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
  // If updating sessions disconnects multiple due to an unsupported chain,
  // we need to wait for the previous session to disconnect before the next
  for await (const session of get(activeSessions)) {
    await updateSession(session, chainId, address);
  }
}

watch([walletKit, address], ([walletKit, address]) => {
  if (walletKit && address) {
    set(activeSessions, getActiveSessions());
    updateSessions(baseSepolia.id.toString(), address);
    setupListeners();
  }
});

async function disconnectSession(topic: string) {
  const kit = get(walletKit);

  await kit!.disconnectSession({
    reason: getSdkError('USER_REJECTED'),
    topic,
  });

  set(activeSessions, getActiveSessions());
}

// Initialize on component mount
onMounted(initializeWalletKit);
</script>

<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">
      WalletKit Integration
    </h2>

    <div class="space-y-4">
      <label
        for="pairUri"
        class="block font-semibold"
      >
        Paste Pair URI from Electron App:
      </label>
      <textarea
        id="pairUri"
        v-model="pairUri"
        placeholder="Paste the Pair URI here"
        rows="4"
        class="w-full p-2 border border-gray-300 rounded-md font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
      <RuiButton
        :disabled="!pairUri.trim() || isConnecting"
        class="disabled:cursor-not-allowed"
        color="success"
        @click="connectWithWalletKit()"
      >
        {{ isConnecting ? 'Connecting...' : 'Start Pairing' }}
      </RuiButton>
    </div>

    <div class="mt-8">
      <h3 class="text-xl font-semibold mb-4">
        Connection Logs
      </h3>
      <div class="border border-gray-300 rounded-md p-4 max-h-[300px] overflow-y-auto bg-gray-50">
        <p
          v-for="(log, index) in logs"
          :key="index"
          class="mb-2 pb-2 border-b border-gray-200 font-mono last:mb-0 last:pb-0 last:border-0"
          :class="{
            'text-blue-600': log.type === 'info',
            'text-green-600': log.type === 'success',
            'text-red-600': log.type === 'error',
          }"
        >
          <span class="text-gray-500 mr-2">{{ log.timestamp }}</span>
          {{ log.message }}
        </p>
      </div>
    </div>
    <div>
      <div
        v-for="session in activeSessions"
        :key="session.topic"
        class="py-3 flex items-center justify-between border-b"
      >
        {{ session.peer.metadata.name }}
        <RuiButton
          variant="text"
          color="error"
          size="sm"
          @click="disconnectSession(session.topic)"
        >
          Disconnect session
        </RuiButton>
      </div>
    </div>
  </div>
</template>
