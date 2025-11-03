<script setup lang="ts">
import WalletConnectionButton from '@/components/wallets/WalletConnectionButton.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { WALLET_MODES } from '@/modules/onchain/wallet-constants';

interface Props {
  isWalletConnected: boolean;
  connectedAddress: string | undefined;
  validatingAddress: boolean;
  isConnecting: boolean;
  isDisconnecting: boolean;
  connectionErrorMessage: string;
}

defineProps<Props>();

const emit = defineEmits<{
  'connect-click': [];
  'disconnect': [];
  'clear-error': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { isWalletConnect, waitingForWalletConfirmation, walletMode } = storeToRefs(useWalletStore());
</script>

<template>
  <div class="space-y-4">
    <!-- Wallet mode selection (only show if not connected) -->
    <div v-if="!isWalletConnected">
      <div class="text-rui-text-secondary text-caption uppercase mb-2">
        {{ t('trade.wallet_mode.label') }}
      </div>
      <RuiButtonGroup
        v-model="walletMode"
        variant="outlined"
        color="primary"
        :required="true"
        size="sm"
      >
        <RuiButton :model-value="WALLET_MODES.LOCAL_BRIDGE">
          {{ t('trade.wallet_mode.local_bridge') }}
        </RuiButton>
        <RuiButton :model-value="WALLET_MODES.WALLET_CONNECT">
          {{ t('trade.wallet_mode.wallet_connect') }}
        </RuiButton>
      </RuiButtonGroup>
    </div>

    <!-- Waiting for wallet confirmation -->
    <RuiAlert
      v-if="waitingForWalletConfirmation"
      type="info"
    >
      {{
        isWalletConnect
          ? t('trade.waiting_for_confirmation.wallet_connect')
          : t('trade.waiting_for_confirmation.not_wallet_connect')
      }}
    </RuiAlert>

    <!-- Connect button -->
    <WalletConnectionButton
      v-if="!isWalletConnected || isDisconnecting"
      :connected="isWalletConnected"
      :loading="isConnecting || isDisconnecting || validatingAddress"
      @click="emit('connect-click')"
    />

    <!-- Connection errors -->
    <RuiAlert
      v-if="connectionErrorMessage"
      type="error"
      variant="default"
      :closeable="true"
      @close="emit('clear-error')"
    >
      <div class="whitespace-pre-line">
        {{ connectionErrorMessage }}
      </div>
    </RuiAlert>

    <!-- Connected address display -->
    <div
      v-if="isWalletConnected"
      class="flex flex-col items-start"
    >
      <div class="text-caption text-rui-text-secondary mb-2">
        {{ t('external_services.gnosispay.siwe.connected_address') }}
      </div>
      <div
        class="border border-default rounded-md px-3 py-1 flex items-center gap-2 font-mono text-sm font-medium mb-3"
      >
        <div class="p-0.5 rounded-full size-3 border border-rui-success-lighter/40">
          <div class="size-full rounded-full bg-rui-success-lighter" />
        </div>
        <HashLink
          :truncate-length="0"
          :text="connectedAddress!"
          location="gnosis"
        />
      </div>
      <RuiButton
        color="primary"
        variant="outlined"
        @click="emit('disconnect')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-unplug"
            size="16"
          />
        </template>
        {{ t('external_services.gnosispay.siwe.disconnect') }}
      </RuiButton>
    </div>
  </div>
</template>
