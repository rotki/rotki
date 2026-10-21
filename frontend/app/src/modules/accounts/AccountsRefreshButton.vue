<script setup lang="ts">
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { useCategoryChainRefresh } from '@/modules/accounts/use-category-chain-refresh';

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

const menuOpen = ref<boolean>(false);

const { isSectionLoading, refreshDisabled } = useBlockchainAccountLoading(() => category);
const { refreshable } = useCategoryChainRefresh(() => category);

/** A single chain has nothing to pick from, so without a menu of its own the button stays plain. */
const hasMenu = computed<boolean>(() => !!slots.menu || get(refreshable).length > 1);

function close(): void {
  set(menuOpen, false);
}

function refreshChain(chain: string): void {
  close();
  emit('refresh', [chain]);
}
</script>

<template>
  <RuiButtonGroup
    variant="outlined"
    color="primary"
  >
    <RuiButton
      data-testid="blockchain-account-refresh"
      :disabled="refreshDisabled"
      :loading="isSectionLoading"
      @click="emit('refresh')"
    >
      <template #prepend>
        <RuiIcon name="lu-refresh-ccw" />
      </template>
      {{ t('common.refresh') }}
    </RuiButton>
    <RuiMenu
      v-if="hasMenu"
      v-model="menuOpen"
      :options="{ placement: 'bottom-end' }"
      :class-names="{ root: 'flex' }"
    >
      <template #activator="{ attrs }">
        <RuiButton
          v-bind="attrs"
          data-testid="blockchain-account-refresh-menu"
          :aria-label="t('account_balances.refresh_menu.label')"
          color="primary"
          variant="outlined"
          class="px-2"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>

      <template v-if="menuOpen">
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
              @click="refreshChain(state.chain)"
            >
              {{ state.name }}
            </RuiButton>
          </div>
        </slot>
      </template>
    </RuiMenu>
  </RuiButtonGroup>
</template>
