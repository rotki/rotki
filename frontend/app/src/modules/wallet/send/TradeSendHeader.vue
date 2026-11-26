<script setup lang="ts">
import { RuiButton, RuiButtonGroup, RuiIcon, RuiProgress, RuiTooltip } from '@rotki/ui-library';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n';
import { WALLET_MODES } from '@/modules/wallet/constants';
import TradeConnectedAddressBadge from '@/modules/wallet/send/TradeConnectedAddressBadge.vue';
import TradeHistoryView from '@/modules/wallet/send/TradeHistoryView.vue';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

defineProps<{
  walletConnected: boolean;
  warnUntrackedAddress: boolean;
  queryingBalances: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  connect: [];
  disconnect: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { isDisconnecting, walletMode } = storeToRefs(useWalletStore());
</script>

<template>
  <div class="h-17 px-6 flex items-center gap-3 border-b border-default">
    <div class="flex-1 min-w-0 flex items-center gap-2">
      <template v-if="!walletConnected">
        <span class="text-sm text-rui-text-secondary shrink-0">{{ t('trade.wallet_mode.label') }}</span>
        <RuiButtonGroup
          v-model="walletMode"
          variant="segmented"
          size="sm"
          required
          data-testid="wallet-mode"
        >
          <RuiButton :model-value="WALLET_MODES.LOCAL_BRIDGE">
            {{ t('trade.wallet_mode.local_bridge') }}
          </RuiButton>
          <RuiButton :model-value="WALLET_MODES.WALLET_CONNECT">
            {{ t('trade.wallet_mode.wallet_connect') }}
          </RuiButton>
        </RuiButtonGroup>
      </template>
      <RuiTooltip
        v-else-if="warnUntrackedAddress && !isDisconnecting"
        class="min-w-0"
        :open-delay="200"
        :options="{ placement: 'bottom-start' }"
        :class-names="{ tooltip: 'max-w-72' }"
      >
        <template #activator>
          <span
            class="flex items-center gap-1.5 text-sm text-rui-warning min-w-0"
            data-testid="untracked-warning"
          >
            <RuiIcon
              name="lu-triangle-alert"
              size="16"
              class="shrink-0"
            />
            <span class="truncate">{{ t('trade.status.not_tracked') }}</span>
          </span>
        </template>
        {{ t('trade.warning.not_tracked') }}
      </RuiTooltip>
      <RuiTooltip
        v-else-if="queryingBalances"
        class="min-w-0"
        :open-delay="200"
        :options="{ placement: 'bottom-start' }"
        :class-names="{ tooltip: 'max-w-72' }"
      >
        <template #activator>
          <span
            class="flex items-center gap-2 text-sm text-rui-text-secondary min-w-0"
            data-testid="querying-balances-warning"
          >
            <RuiProgress
              circular
              variant="indeterminate"
              color="primary"
              size="14"
              thickness="2"
              class="shrink-0"
            />
            <span class="truncate">{{ t('trade.status.updating_balances') }}</span>
          </span>
        </template>
        {{ t('trade.warning.query_on_progress') }}
      </RuiTooltip>
    </div>
    <div class="flex items-center gap-1 shrink-0">
      <TradeConnectedAddressBadge
        v-if="walletConnected"
        :loading="loading"
        @connect="emit('connect')"
        @disconnect="emit('disconnect')"
      />
      <TradeHistoryView />
    </div>
  </div>
</template>
