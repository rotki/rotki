<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { SkipState, useAccountSkipQueries } from '@/modules/accounts/table/use-account-skip-queries';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { address, chains, disabled = false } = defineProps<{
  address: string;
  chains: string[];
  disabled?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { items, locked, pending, state, toggleAll, toggleChain } = useAccountSkipQueries(
  () => address,
  () => chains,
);

const perChain = computed<boolean>(() => get(items).length > 1);

/** What "all" means: chains switched off whole are listed, but no row action reaches them. */
const actionable = computed<number>(() => get(items).filter(item => !item.wholeChain).length);

const color = computed<'error' | 'warning' | undefined>(() => {
  const current = get(state);
  if (current === SkipState.ALL)
    return 'error';
  return current === SkipState.PARTIAL ? 'warning' : undefined;
});

const allSkipped = computed<boolean>(() => get(state) === SkipState.ALL);

/**
 * Inert rather than `disabled` while locked, so the tooltip explaining why still opens.
 *
 * @remarks
 * A natively disabled button dispatches no mouse events, and the tooltip listens on a wrapper drawn
 * tightly around it, so disabling the one state that exists to be explained is what hides the
 * explanation. Opening the menu is already blocked on `locked`, and this covers the click.
 */
function activate(): void {
  if (get(locked) || get(perChain))
    return;
  startPromise(toggleAll());
}

const tooltip = computed<string>(() => {
  if (get(locked))
    return t('account_balances.skip_queries.entire_chain');
  if (get(perChain))
    return t('account_balances.skip_queries.menu');

  const chain = get(items)[0];
  return chain.skipped
    ? t('account_balances.skip_queries.resume', { chains: chain.name })
    : t('account_balances.skip_queries.skip', { chains: chain.name });
});
</script>

<template>
  <RuiMenu
    :disabled="!perChain || locked"
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            v-bind="perChain ? attrs : {}"
            variant="text"
            icon
            data-testid="account-skip-queries"
            :disabled="disabled || pending"
            :aria-disabled="locked || undefined"
            :class="{ 'opacity-50 cursor-not-allowed': locked }"
            :color="color"
            @click="activate()"
          >
            <RuiIcon
              size="16"
              name="lu-ban"
            />
          </RuiButton>
        </template>
        {{ tooltip }}
      </RuiTooltip>
    </template>

    <div class="min-w-[16rem]">
      <RuiButton
        variant="list"
        size="sm"
        :disabled="pending"
        data-testid="account-skip-queries-all"
        @click="toggleAll()"
      >
        <template #prepend>
          <RuiIcon
            size="18"
            :name="allSkipped ? 'lu-circle-check' : 'lu-ban'"
          />
        </template>
        {{ allSkipped
          ? t('account_balances.skip_queries.resume_all', { count: actionable }, actionable)
          : t('account_balances.skip_queries.skip_all', { count: actionable }, actionable) }}
      </RuiButton>

      <RuiDivider class="my-1" />

      <RuiButton
        v-for="item in items"
        :key="item.chain"
        variant="list"
        size="sm"
        :disabled="pending || item.wholeChain"
        data-testid="account-skip-queries-chain"
        :data-chain="item.chain"
        @click="toggleChain(item.chain)"
      >
        <template #prepend>
          <ChainIcon
            :chain="item.chain"
            size="18px"
          />
        </template>
        <div class="flex items-baseline justify-between gap-6 w-full">
          <span class="truncate">{{ item.name }}</span>
          <span
            v-if="item.wholeChain || item.skipped"
            class="text-caption font-normal text-rui-text-secondary shrink-0"
            data-testid="account-skip-queries-chain-state"
          >
            {{ item.wholeChain
              ? t('account_balances.skip_queries.chain_whole')
              : t('account_balances.skip_queries.chain_skipped') }}
          </span>
        </div>
      </RuiButton>
    </div>
  </RuiMenu>
</template>
