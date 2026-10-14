<script setup lang="ts">
import HashLink from '@/modules/shell/components/HashLink.vue';
import { WALLET_MODES } from '@/modules/wallet/constants';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
import WalletConnectionButton from '@/modules/wallet/WalletConnectionButton.vue';

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
  <div class="flex flex-col items-start gap-3">
    <div
      v-if="!isWalletConnected"
      class="flex flex-col gap-1.5"
    >
      <div class="text-sm font-medium text-rui-text-secondary">
        {{ t('trade.wallet_mode.label') }}
      </div>
      <RuiButtonGroup
        v-model="walletMode"
        variant="outlined"
        color="primary"
        required
        size="sm"
      >
        <RuiButton :model-value="WALLET_MODES.LOCAL_BRIDGE">
          {{ t('trade.wallet_mode.local_bridge') }}
        </RuiButton>
        <RuiButton :model-value="WALLET_MODES.WALLET_CONNECT">
          {{ t('trade.wallet_mode.wallet_connect') }}
        </RuiButton>
      </RuiButtonGroup>
      <div
        class="text-xs text-rui-text-secondary"
        data-testid="gnosis-pay-wallet-mode-hint"
      >
        {{ walletMode === WALLET_MODES.WALLET_CONNECT
          ? t('external_services.gnosispay.siwe.mode_hint.wallet_connect')
          : t('external_services.gnosispay.siwe.mode_hint.local_bridge') }}
      </div>
    </div>

    <RuiAlert
      v-if="waitingForWalletConfirmation"
      type="info"
      class="w-full"
    >
      {{
        isWalletConnect
          ? t('trade.waiting_for_confirmation.wallet_connect')
          : t('trade.waiting_for_confirmation.not_wallet_connect')
      }}
    </RuiAlert>

    <WalletConnectionButton
      v-if="!isWalletConnected || isDisconnecting"
      :connected="isWalletConnected"
      :loading="isConnecting || isDisconnecting || validatingAddress"
      @click="emit('connect-click')"
    />

    <RuiAlert
      v-if="connectionErrorMessage"
      type="error"
      variant="default"
      class="w-full"
      closeable
      @close="emit('clear-error')"
    >
      <div class="whitespace-pre-line">
        {{ connectionErrorMessage }}
      </div>
    </RuiAlert>

    <div
      v-if="isWalletConnected"
      class="flex w-full flex-col gap-1.5"
    >
      <div class="text-sm font-medium text-rui-text-secondary">
        {{ t('external_services.gnosispay.siwe.connected_address') }}
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex min-w-0 items-center gap-2 rounded-rui-control border border-rui-divider px-3 py-1.5 font-mono text-sm">
          <span class="size-2 shrink-0 rounded-full bg-rui-success" />
          <HashLink
            :truncate-length="0"
            :text="connectedAddress!"
            location="gnosis"
          />
        </div>
        <RuiButton
          color="primary"
          variant="text"
          size="sm"
          @click="emit('disconnect')"
        >
          <template #prepend>
            <RuiIcon
              name="lu-unplug"
              size="14"
            />
          </template>
          {{ t('external_services.gnosispay.siwe.disconnect') }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
