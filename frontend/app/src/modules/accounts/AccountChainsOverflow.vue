<script setup lang="ts">
import { startPromise } from '@shared/utils';
import AccountChainSkipButton from '@/modules/accounts/AccountChainSkipButton.vue';
import { type SkipChainItem, useAccountSkipQueries } from '@/modules/accounts/table/use-account-skip-queries';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

export interface AccountChainState {
  chain: string;
  enabled: boolean;
  skipped: boolean;
  detected: boolean;
}

const open = defineModel<boolean>('open', { default: false });

const { items, skipAddress } = defineProps<{
  items: AccountChainState[];
  /** The address a skip rule would name, on the rows the backend can match one against. */
  skipAddress?: string;
}>();

const emit = defineEmits<{
  toggle: [change: { chain: string; enabled: boolean }];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();

/**
 * One skip view for every listed chain, rather than one per chain.
 *
 * @remarks
 * Without an address it is never asked anything: the skip buttons only render with one.
 */
const { items: skipItems, labelFor, pending, toggleChain } = useAccountSkipQueries(
  () => skipAddress ?? '',
  () => items.map(({ chain }) => chain),
);

const skipItemOf = (chain: string): SkipChainItem | undefined => get(skipItems).find(item => item.chain === chain);

/** Closes on the way out, so a row waiting on its open menus never waits on one that is gone. */
onBeforeUnmount(() => {
  if (get(open))
    set(open, false);
});

/** Whether any hidden chain is filtered out, so the counter shows it the way a dimmed icon would. */
const anyHiddenFiltered = computed<boolean>(() => items.some(item => !item.enabled));
</script>

<template>
  <RuiMenu
    v-model="open"
    lazy
    :options="{ placement: 'bottom-start' }"
  >
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
      <div
        v-for="item in items"
        :key="item.chain"
        class="flex items-center gap-1 pr-2"
      >
        <RuiButton
          variant="list"
          size="sm"
          class="grow min-w-0"
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
        <AccountChainSkipButton
          v-if="skipAddress !== undefined"
          :chain="item.chain"
          :label="labelFor(item.chain)"
          :skipped="item.skipped"
          :locked="skipItemOf(item.chain)?.wholeChain ?? false"
          :pending="pending"
          @toggle="startPromise(toggleChain(item.chain))"
        />
      </div>
    </div>
  </RuiMenu>
</template>
