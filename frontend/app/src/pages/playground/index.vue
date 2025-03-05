<script setup lang="ts">
import AmountInput from '@/components/inputs/AmountInput.vue';
import { WagmiAdapter } from '@reown/appkit-adapter-wagmi';
import { baseSepolia } from '@reown/appkit/networks';
import { createAppKit, useAppKitProvider } from '@reown/appkit/vue';
import { get, set } from '@vueuse/core';
import { Core } from '@walletconnect/core';
import { BrowserProvider, formatEther, parseUnits } from 'ethers';
import { onUnmounted, ref } from 'vue';

const PROJECT_ID = 'eca1bd3842e084bfc8ef309b6eb584db';

/* Wallet State Management */
const connected = ref(false);
const walletAddress = ref<string | null>(null);
const connectedChainId = ref<bigint | null>(null);
const ethBalance = ref<string>('0.0');
const sendToAddress = ref<string>('');
const sendAmount = ref<string>('');
const pairUri = ref<string>('');

const metadata = {
  description: 'Rotki Active Management',
  icons: ['https://raw.githubusercontent.com/rotki/data/refs/heads/main/assets/default_icons/website_logo.png'],
  name: 'Rotki Active Management',
  url: 'https://rotki.com',
};

const wagmiAdapter = new WagmiAdapter({
  networks: [baseSepolia],
  projectId: PROJECT_ID,
  ssr: false,
});

/* Initialize AppKit */
const appKit = createAppKit({
  adapters: [wagmiAdapter],
  allowUnsupportedChain: true,
  features: {
    email: false,
    socials: false,
  },
  metadata,
  networks: [baseSepolia],
  projectId: PROJECT_ID,
});

/* Subscribe to Account Changes */
appKit.subscribeAccount(async (account) => {
  set(connected, account.isConnected);
  set(walletAddress, account.isConnected ? account.address : null);

  if (get(connected)) {
    console.log('Wallet connected:', get(walletAddress));
    await fetchBalance();
  }
  else {
    console.log('Wallet disconnected');
    resetWalletState();
  }
});

/* Subscribe to AppKit State Changes */
appKit.subscribeState((state) => {
  if (!state.open)
    console.log('AppKit modal closed');
});

/* Reset Wallet State */
function resetWalletState() {
  set(connectedChainId, null);
  set(ethBalance, '0.0');
  set(sendToAddress, '');
  set(sendAmount, '');
}

/* Fetch ETH Balance */
async function fetchBalance() {
  const { walletProvider } = useAppKitProvider('eip155');
  const browserProvider = new BrowserProvider(walletProvider as any);

  if (get(walletAddress)) {
    const balance = await browserProvider.getBalance(get(walletAddress)!);
    const formattedBalance = formatEther(balance); // Convert from Wei to human-readable format
    set(ethBalance, formattedBalance);
    console.log('ETH Balance:', get(ethBalance));
  }
}

/* Set Maximum Send Amount */
function setMaxSendAmount() {
  set(sendAmount, get(ethBalance));
}

/* Send ETH */
async function sendEth() {
  if (!get(walletAddress) || !get(sendToAddress) || !get(sendAmount)) {
    console.log('Ensure all fields are correctly filled.');
    return;
  }

  try {
    const { walletProvider } = useAppKitProvider('eip155');
    const browserProvider = new BrowserProvider(walletProvider as any);
    const signer = await browserProvider.getSigner();

    console.log(signer);

    const tx = await signer.sendTransaction({
      to: get(sendToAddress),
      value: parseUnits(get(sendAmount), 'ether'),
    });
    console.log('Transaction sent. Hash:', tx.hash);

    await tx.wait(); // Wait for transaction confirmation
    console.log('Transaction confirmed:', tx.hash);
    await fetchBalance(); // Refresh balance
  }
  catch (error) {
    console.error('Transaction failed:', error);
  }
}

/* Disconnect Wallet */
async function disconnectWallet() {
  await appKit.disconnect();
  resetWalletState();
  console.log('Wallet disconnected manually.');
}

/* WalletConnect Core Setup */
const core = new Core({
  projectId: PROJECT_ID,
});

async function generatePairUri() {
  try {
    const pairing = await core.pairing.create();
    console.log('Pair URI generated:', pairing.uri);
    set(pairUri, pairing.uri);
  }
  catch (error) {
    console.error('Error generating Pair URI:', error);
  }
}

onUnmounted(async () => {
  await appKit.disconnect();
  console.log('AppKit disconnected');
});
</script>

<template>
  <div class="container !max-w-lg py-10">
    <h1 class="text-2xl font-bold mb-4">
      Base Sepolia ETH Wallet
    </h1>

    <!-- Connection Section -->
    <div v-if="!connected">
      <RuiButton
        color="primary"
        class="w-full"
        @click="appKit.open()"
      >
        Connect Wallet
      </RuiButton>
    </div>

    <div v-else>
      <p><strong>Wallet Address:</strong> {{ walletAddress }}</p>
      <p><strong>ETH Balance:</strong> {{ ethBalance }} ETH</p>

      <div class="mt-4">
        <div
          class="flex flex-col gap-2"
        >
          <h2 class="text-xl font-bold">
            Send ETH
          </h2>
          <RuiTextField
            v-model="sendToAddress"
            variant="outlined"
            hide-details
            dense
            color="primary"
            label="Recipient Address"
          />
          <div class="flex items-center">
            <AmountInput
              v-model="sendAmount"
              variant="outlined"
              dense
              class="flex-1"
              hide-details
              color="primary"
              label="Amount (ETH)"
            />
            <RuiButton
              color="secondary"
              @click="setMaxSendAmount()"
            >
              Max
            </RuiButton>
          </div>

          <RuiButton
            color="primary"
            class="mt-4"
            @click="sendEth()"
          >
            Send ETH
          </RuiButton>
        </div>
        <RuiButton
          color="error"
          class="mt-2 w-full"
          @click="disconnectWallet()"
        >
          Disconnect Wallet
        </RuiButton>
      </div>
    </div>
  </div>
</template>
