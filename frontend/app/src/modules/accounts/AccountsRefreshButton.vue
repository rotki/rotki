<script setup lang="ts">
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { useCategoryChainRefresh } from '@/modules/accounts/use-category-chain-refresh';
import RefreshSplitButton from '@/modules/shell/components/RefreshSplitButton.vue';

const { category } = defineProps<{
  category: string;
}>();

const emit = defineEmits<{
  refresh: [chains?: string[]];
}>();

const slots = defineSlots<{
  /** Replaces the per-chain list in the options menu. */
  menu?: (props: { close: () => void }) => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const { isSectionLoading, refreshDisabled } = useBlockchainAccountLoading(() => category);
const { refreshable } = useCategoryChainRefresh(() => category);

/** A single chain has nothing to pick from, so without a menu of its own the button stays plain. */
const hasMenu = computed<boolean>(() => !!slots.menu || get(refreshable).length > 1);

function refreshChain(close: () => void, chain: string): void {
  close();
  emit('refresh', [chain]);
}
</script>

<template>
  <RefreshSplitButton
    test-id="blockchain-account-refresh"
    :menu-label="t('account_balances.refresh_menu.label')"
    :loading="isSectionLoading"
    :disabled="refreshDisabled"
    :hide-menu="!hasMenu"
    @refresh="emit('refresh')"
  >
    <template #default="{ close, isOpen }">
      <template v-if="isOpen">
        <slot
          name="menu"
          :close="close"
        >
          <div class="w-72 max-w-full py-1">
            <div class="px-4 pt-2 pb-1 text-caption uppercase tracking-wide text-rui-text-secondary">
              {{ t('account_balances.refresh_menu.one_chain') }}
            </div>
            <RuiButton
              v-for="state in refreshable"
              :key="state.chain"
              variant="list"
              :disabled="refreshDisabled"
              data-testid="blockchain-account-refresh-chain"
              @click="refreshChain(close, state.chain)"
            >
              {{ state.name }}
            </RuiButton>
          </div>
        </slot>
      </template>
    </template>
  </RefreshSplitButton>
</template>
