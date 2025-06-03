<script setup lang="ts">
import TradeConnectedAddressBadge from '@/modules/onchain/send/TradeConnectedAddressBadge.vue';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import Pairing from '@/modules/onchain/wallet-bridge/Pairing.vue';

definePage({
  meta: {
    layout: 'plain',
    title: 'rotki browser wallet bridge',
  },
});

const { t } = useI18n({ useScope: 'global' });
const walletStore = useWalletStore();
const { connected, connectedAddress, connectedChainId, supportedChainsIdForConnectedAccount } = storeToRefs(walletStore);
const { disconnect } = walletStore;

const firstStep = '1';
</script>

<template>
  <div class="overflow-auto w-full text-rui-text">
    <div class="container !max-w-lg py-6 min-h-screen">
      <h4 class="text-h4 mb-4">
        {{ t('trade.bridge.title') }}
      </h4>

      <div class="py-4">
        <div class="flex gap-2">
          <div class="rounded-full bg-rui-primary text-white size-8 flex items-center justify-center font-bold">
            {{ firstStep }}
          </div>
          <div class="mt-1">
            <div class="mb-4 font-bold">
              {{ t('trade.bridge.connect_the_signer') }}
            </div>
            <div class="flex gap-2 flex-1">
              <TradeConnectedAddressBadge />
              <RuiButton
                v-if="connectedAddress && connectedChainId"
                color="error"
                @click="disconnect()"
              >
                {{ t('trade.actions.disconnect') }}
              </RuiButton>
            </div>
          </div>
        </div>
      </div>

      <Pairing
        :connected="connected"
        :address="connectedAddress"
        :connected-chain-id="connectedChainId"
        :supported-chain-ids="supportedChainsIdForConnectedAccount"
      />
    </div>
  </div>
</template>
