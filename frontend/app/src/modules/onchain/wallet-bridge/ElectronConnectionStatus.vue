<script setup lang="ts">
const props = defineProps<{
  isConnected: boolean;
  isConnecting: boolean;
  error?: string;
  onRetryConnection: () => void;
  onDisconnect: () => void;
}>();

const { t } = useI18n({ useScope: 'global' });

const { error, isConnected, isConnecting, onDisconnect, onRetryConnection } = toRefs(props);
</script>

<template>
  <div class="mt-6 p-4 border border-default rounded-lg bg-rui-grey-50/50 dark:bg-rui-grey-900/50">
    <h5 class="font-bold mb-3">
      {{ t('trade.bridge.electron_connection') }}
    </h5>

    <div class="flex items-center gap-3">
      <div
        class="w-3 h-3 rounded-full"
        :class="[
          isConnected ? 'bg-green-500'
          : isConnecting ? 'bg-yellow-500 animate-pulse'
            : 'bg-red-500',
        ]"
      />
      <span class="text-sm">
        {{ isConnected
          ? t('trade.bridge.connected_to_electron')
          : isConnecting
            ? t('trade.bridge.connecting_to_electron')
            : t('trade.bridge.disconnected_from_electron')
        }}
      </span>
    </div>

    <div class="mt-1 text-sm text-rui-text-secondary">
      {{ isConnected
        ? t('trade.bridge.electron_ready_message')
        : isConnecting
          ? t('trade.bridge.electron_connecting_message')
          : t('trade.bridge.electron_disconnected_message')
      }}
    </div>

    <!-- Error Display -->
    <RuiAlert
      v-if="error && !isConnected && !isConnecting"
      type="error"
      class="mt-3"
    >
      <div class="mt-0.5">
        {{ error }}
      </div>
    </RuiAlert>

    <div class="mt-4 flex gap-2">
      <RuiButton
        v-if="!isConnected"
        size="sm"
        color="primary"
        :disabled="isConnecting"
        @click="onRetryConnection()"
      >
        {{ isConnecting
          ? t('trade.bridge.connecting')
          : t('trade.bridge.retry_connection')
        }}
      </RuiButton>

      <RuiButton
        v-if="isConnected"
        size="sm"
        color="error"
        variant="outlined"
        @click="onDisconnect()"
      >
        {{ t('trade.bridge.disconnect_electron') }}
      </RuiButton>
    </div>
  </div>
</template>
