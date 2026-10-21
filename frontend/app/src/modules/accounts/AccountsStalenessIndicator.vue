<script setup lang="ts">
import { formatTimeAgo } from '@vueuse/core';
import { type ChainRefreshState, useCategoryChainRefresh } from '@/modules/accounts/use-category-chain-refresh';

const { category } = defineProps<{
  category: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const now = useNow({ scheduler: tick => useIntervalFn(tick, 30_000) });

const { chains, oldest, refreshable } = useCategoryChainRefresh(() => category);

const summary = computed<string>(() => {
  const state = get(oldest);
  if (!state)
    return '';

  const time = describeAge(state);
  return get(refreshable).length > 1 ? t('account_balances.staleness.oldest', { chain: state.name, time }) : time;
});

function describeAge(state: ChainRefreshState): string {
  if (state.skipped)
    return t('account_balances.staleness.skipped');

  if (state.timestamp === undefined)
    return t('account_balances.staleness.never');

  return formatTimeAgo(new Date(state.timestamp * 1000), {}, get(now));
}
</script>

<template>
  <RuiTooltip
    v-if="oldest"
    class="inline-flex"
    :options="{ placement: 'bottom' }"
    :open-delay="200"
  >
    <template #activator>
      <span
        class="inline-flex items-center gap-1 text-xs text-rui-text-secondary whitespace-nowrap"
        data-testid="accounts-staleness"
      >
        <RuiIcon
          name="lu-clock"
          size="14"
        />
        {{ summary }}
      </span>
    </template>
    <div class="flex flex-col gap-1 min-w-48">
      <span class="font-medium">{{ t('account_balances.staleness.title') }}</span>
      <span
        v-for="state in chains"
        :key="state.chain"
        class="flex justify-between gap-4"
        data-testid="accounts-staleness-chain"
      >
        <span>{{ state.name }}</span>
        <span>{{ describeAge(state) }}</span>
      </span>
    </div>
  </RuiTooltip>
</template>
