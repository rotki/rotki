<script setup lang="ts">
import DetectEvmAccounts from '@/components/accounts/balances/DetectEvmAccounts.vue';
import DetectTokenChainsSelection from '@/components/accounts/balances/DetectTokenChainsSelection.vue';
import { useRefresh } from '@/composables/balances/refresh';
import { useConfirmStore } from '@/store/confirm';

defineProps<{
  isDetectingTokens: boolean;
  refreshDisabled: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { handleBlockchainRefresh } = useRefresh();
const { show } = useConfirmStore();

function redetectAllClicked(): void {
  show({
    message: t('account_balances.detect_tokens.confirmation.message'),
    title: t('account_balances.detect_tokens.confirmation.title'),
    type: 'info',
  }, () => {
    handleBlockchainRefresh(undefined, true);
  });
}
</script>

<template>
  <div class="flex items-center gap-2 flex-1">
    <RuiButtonGroup
      variant="outlined"
      color="primary"
    >
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            class="py-2 !outline-0 rounded-none"
            variant="outlined"
            color="primary"
            :loading="isDetectingTokens"
            :disabled="refreshDisabled"
            @click="redetectAllClicked()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>

            {{ t('account_balances.detect_tokens.tooltip.redetect') }}
          </RuiButton>
        </template>
        {{ t('account_balances.detect_tokens.tooltip.redetect_all') }}
      </RuiTooltip>

      <DetectTokenChainsSelection @redetect:all="redetectAllClicked()" />
    </RuiButtonGroup>

    <DetectEvmAccounts />
  </div>
</template>
