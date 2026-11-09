<script setup lang="ts">
import { CLIENT_CONFIG } from './bridge-config';
import StatusDot from './StatusDot.vue';
import { BridgeConnectionPhase, type BridgeConnectionState } from './use-wallet-proxy-client';

const { state, error, onRetryConnection, onDisconnect } = defineProps<{
  state: BridgeConnectionState;
  error?: string;
  onRetryConnection: () => void;
  onDisconnect: () => void;
}>();

const { t } = useI18n({ useScope: 'global' });

const isConnected = computed<boolean>(() => state.phase === BridgeConnectionPhase.connected);

const isExhausted = computed<boolean>(() => state.phase === BridgeConnectionPhase.retriesExhausted);

/** The attempt to display while still trying: 0 for a first connect, which is not a retry. */
const retryAttempt = computed<number | undefined>(() => {
  if (state.phase === BridgeConnectionPhase.retryWaiting || state.phase === BridgeConnectionPhase.connecting)
    return state.attempt;
  return undefined;
});

const isTrying = computed<boolean>(() => get(retryAttempt) !== undefined);

const dotStatus = computed<'connected' | 'connecting' | 'error'>(() => {
  if (get(isConnected))
    return 'connected';
  return get(isTrying) ? 'connecting' : 'error';
});

const label = computed<string>(() => {
  const attempt = get(retryAttempt);
  if (get(isConnected))
    return t('trade.bridge.connected_to_electron');
  if (attempt === undefined)
    return t('trade.bridge.disconnected_from_electron');
  return attempt === 0
    ? t('trade.bridge.connecting_to_electron')
    : t('trade.bridge.reconnecting_to_electron', { attempt: attempt + 1, max: CLIENT_CONFIG.MAX_RETRIES });
});

const message = computed<string>(() => {
  if (get(isConnected))
    return t('trade.bridge.electron_ready_message');
  if (get(isTrying))
    return t('trade.bridge.electron_connecting_message');
  return get(isExhausted)
    ? t('trade.bridge.electron_retries_exhausted_message')
    : t('trade.bridge.electron_disconnected_message');
});
</script>

<template>
  <RuiCard divide>
    <template #header>
      {{ t('trade.bridge.electron_connection') }}
    </template>

    <div class="flex items-start gap-3">
      <StatusDot
        class="mt-1 shrink-0"
        :status="dotStatus"
        :animate="isTrying"
      />
      <div class="flex-1 min-w-0">
        <p
          class="text-sm font-medium"
          data-testid="bridge-connection-label"
        >
          {{ label }}
        </p>
        <p
          class="text-sm text-rui-text-secondary"
          data-testid="bridge-connection-message"
        >
          {{ message }}
        </p>
      </div>
      <RuiButton
        v-if="isConnected"
        size="sm"
        color="error"
        variant="outlined"
        data-testid="bridge-connection-disconnect"
        @click="onDisconnect()"
      >
        {{ t('trade.bridge.disconnect_electron') }}
      </RuiButton>
      <RuiButton
        v-else
        size="sm"
        color="primary"
        :disabled="isTrying"
        data-testid="bridge-connection-connect"
        @click="onRetryConnection()"
      >
        {{ isTrying ? t('trade.bridge.connecting') : t('trade.bridge.retry_connection') }}
      </RuiButton>
    </div>

    <RuiAlert
      v-if="error && !isConnected && !isTrying"
      type="error"
      class="mt-4"
      data-testid="bridge-connection-error"
    >
      {{ error }}
    </RuiAlert>
  </RuiCard>
</template>
