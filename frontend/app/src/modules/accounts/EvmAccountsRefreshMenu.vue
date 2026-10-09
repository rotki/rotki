<script setup lang="ts">
import { startPromise } from '@shared/utils';
import DetectEvmAccounts from '@/modules/accounts/balances/DetectEvmAccounts.vue';
import DetectTokenChainsSelection from '@/modules/accounts/balances/DetectTokenChainsSelection.vue';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import BlockchainBalanceRefreshBehaviourMenu from '@/modules/balances/BlockchainBalanceRefreshBehaviourMenu.vue';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

/** The menu shows its entries, or the chain picker one of them leads to. */
const pickingChains = ref<boolean>(false);

/** A full re-detect is slow, so its entry asks in place before it runs, rather than in a dialog. */
const confirmingAll = ref<boolean>(false);

const { isDetectingTokens, refreshDisabled } = useBlockchainAccountLoading('evm');
const { massDetectTokens } = useBalanceRefresh();

/** Asks for the full re-detect, from its own entry or from the picker with every chain chosen. */
function askRedetectAll(): void {
  set(pickingChains, false);
  set(confirmingAll, true);
}

function redetectAll(): void {
  set(confirmingAll, false);
  emit('close');
  startPromise(massDetectTokens());
}
</script>

<template>
  <!--
    Everything that fetches newer data for the EVM accounts behind one Refresh button: the refresh
    itself is the button, token and account detection are here, so the page carries one entry point.
  -->
  <div v-if="pickingChains">
    <div class="flex items-center gap-1 px-2 py-1 border-b border-default">
      <RuiButton
        variant="text"
        icon
        size="sm"
        :aria-label="t('common.actions.back')"
        data-testid="refresh-menu-back"
        @click="pickingChains = false"
      >
        <RuiIcon
          size="18"
          name="lu-arrow-left"
        />
      </RuiButton>
      <span class="text-subtitle-2">{{ t('account_balances.detect_tokens.menu.chains_title') }}</span>
    </div>
    <DetectTokenChainsSelection
      @redetect:all="askRedetectAll()"
      @done="emit('close')"
    />
  </div>
  <div
    v-else
    class="w-88 max-w-full py-1"
  >
    <div class="px-4 pt-2 pb-1 text-caption uppercase tracking-wide text-rui-text-secondary">
      {{ t('account_balances.detect_tokens.menu.section') }}
    </div>
    <div
      v-if="confirmingAll"
      class="mx-2 my-1 rounded-md bg-rui-neutral-100 dark:bg-rui-neutral-800 px-3 py-2"
      data-testid="refresh-menu-redetect-confirm"
    >
      <div class="text-body-2 font-medium">
        {{ t('account_balances.detect_tokens.confirmation.title') }}
      </div>
      <div class="text-caption text-rui-text-secondary">
        {{ t('account_balances.detect_tokens.confirmation.message') }}
      </div>
      <div class="flex justify-end gap-2 mt-2">
        <RuiButton
          size="sm"
          variant="text"
          @click="confirmingAll = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          size="sm"
          color="primary"
          data-testid="refresh-menu-redetect-confirm-run"
          @click="redetectAll()"
        >
          {{ t('account_balances.detect_tokens.selection.redetect') }}
        </RuiButton>
      </div>
    </div>
    <RuiButton
      v-else
      variant="list"
      :disabled="refreshDisabled || isDetectingTokens"
      data-testid="refresh-menu-redetect-all"
      @click="askRedetectAll()"
    >
      <template #prepend>
        <RuiIcon
          size="18"
          name="lu-refresh-ccw"
        />
      </template>
      <span class="flex flex-col items-start text-left">
        <span>{{ t('account_balances.detect_tokens.tooltip.redetect') }}</span>
        <span class="text-caption font-normal text-rui-text-secondary whitespace-normal">
          {{ t('account_balances.detect_tokens.menu.all_description') }}
        </span>
      </span>
    </RuiButton>
    <RuiButton
      variant="list"
      :disabled="refreshDisabled || isDetectingTokens"
      data-testid="refresh-menu-redetect-chains"
      @click="pickingChains = true"
    >
      <template #prepend>
        <RuiIcon
          size="18"
          name="lu-list-checks"
        />
      </template>
      <span class="flex flex-col items-start text-left grow">
        <span>{{ t('account_balances.detect_tokens.menu.chains_title') }}</span>
        <span class="text-caption font-normal text-rui-text-secondary whitespace-normal">
          {{ t('account_balances.detect_tokens.menu.chains_description') }}
        </span>
      </span>
      <template #append>
        <RuiIcon
          size="16"
          name="lu-chevron-right"
        />
      </template>
    </RuiButton>
    <DetectEvmAccounts />
    <RuiDivider class="my-1" />
    <BlockchainBalanceRefreshBehaviourMenu />
  </div>
</template>
