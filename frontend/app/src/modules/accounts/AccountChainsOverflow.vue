<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

export interface AccountChainState {
  chain: string;
  enabled: boolean;
  skipped: boolean;
  detected: boolean;
}

const { items } = defineProps<{
  items: AccountChainState[];
}>();

const emit = defineEmits<{
  toggle: [change: { chain: string; enabled: boolean }];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();

/** Whether any hidden chain is filtered out, so the counter shows it the way a dimmed icon would. */
const anyHiddenFiltered = computed<boolean>(() => items.some(item => !item.enabled));
</script>

<template>
  <!--
    The chains past the row's visible few, so a wide account no longer pushes the table sideways.
    Each entry keeps the icon's own click, filtering the chain in or out of the row's totals.
  -->
  <RuiMenu :options="{ placement: 'bottom-start' }">
    <template #activator="{ attrs }">
      <button
        v-bind="attrs"
        type="button"
        class="h-6 px-1.5 rounded-full text-xs font-medium text-rui-text-secondary hover:bg-rui-hover cursor-pointer focus-visible:focus-ring"
        :class="{ 'underline decoration-dotted': anyHiddenFiltered }"
        :aria-label="t('account_balances.chain_filter.more', { count: items.length })"
        data-testid="account-chains-more"
      >
        +{{ items.length }}
      </button>
    </template>

    <div class="min-w-56 py-1">
      <RuiButton
        v-for="item in items"
        :key="item.chain"
        variant="list"
        size="sm"
        data-testid="account-chains-more-item"
        :data-chain="item.chain"
        @click="emit('toggle', { chain: item.chain, enabled: !item.enabled })"
      >
        <template #prepend>
          <ChainIcon
            :chain="item.chain"
            size="18px"
            :class="{ 'opacity-40': !item.enabled }"
          />
        </template>
        <div class="flex items-baseline justify-between gap-6 w-full">
          <span
            class="truncate"
            :class="{ 'text-rui-text-secondary': !item.enabled }"
          >
            {{ getChainName(item.chain) }}
          </span>
          <span
            v-if="!item.enabled || item.skipped"
            class="text-caption font-normal text-rui-text-secondary shrink-0"
          >
            {{ item.skipped ? t('account_balances.skip_queries.chain_skipped') : t('account_balances.chain_filter.excluded') }}
          </span>
        </div>
      </RuiButton>
    </div>
  </RuiMenu>
</template>
