<script setup lang="ts">
import { useInterop } from '@/composables/electron-interop';
import TradeConnectedAddressBadge from '@/modules/onchain/send/TradeConnectedAddressBadge.vue';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import Pairing from '@/modules/onchain/wallet-bridge/Pairing.vue';
import { onUnmounted } from 'vue';

definePage({
  meta: {
    layout: 'plain',
  },
});

const { t } = useI18n();
const walletStore = useWalletStore();
const { connected, connectedAddress, connectedChainId } = storeToRefs(walletStore);
const { disconnect } = walletStore;

onUnmounted(async () => {
  await disconnect();
});

const { isPackaged } = useInterop();
</script>

<template>
  <div class="container !max-w-lg py-6 min-h-screen">
    <h4 class="text-h4 mb-4">
      {{ t('trade.bridge.title') }}
    </h4>

    <div class="flex gap-2">
      <TradeConnectedAddressBadge />
      <RuiButton
        v-if="connectedAddress && connectedChainId"
        color="error"
        @click="disconnect()"
      >
        {{ t('trade.actions.disconnect') }}
      </RuiButton>
    </div>

    <Pairing
      v-if="!isPackaged && connected && connectedAddress && connectedChainId"
      class="mt-8 border-t border-default py-8"
      :address="connectedAddress"
      :connected-chain-id="connectedChainId"
    />
  </div>
</template>
