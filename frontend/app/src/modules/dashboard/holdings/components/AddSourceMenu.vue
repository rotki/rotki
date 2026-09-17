<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationAsRelative } from 'vue-router';
import type { RouteName } from '@/types/router';

interface AddOption {
  readonly key: string;
  readonly icon: RuiIcons;
  readonly label: string;
  /** The page whose add dialog opens; `?add=true` is appended on navigation. */
  readonly to: RouteLocationAsRelative;
}

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

/** Checks the params against this one route, which the union of every route would not. */
function route<Name extends RouteName>(to: RouteLocationAsRelative<Name>): RouteLocationAsRelative {
  return to;
}

const options = computed<AddOption[]>(() => [
  { icon: 'lu-evm-accounts', key: 'evm', label: t('dashboard.blockchain_balances.categories.evm'), to: route({ name: '/accounts/evm/[[tab]]', params: { tab: 'accounts' } }) },
  { icon: 'lu-bitcoin-accounts', key: 'bitcoin', label: t('dashboard.blockchain_balances.categories.bitcoin'), to: route({ name: '/accounts/bitcoin/' }) },
  { icon: 'lu-blockchain', key: 'solana', label: t('dashboard.blockchain_balances.categories.solana'), to: route({ name: '/accounts/solana/' }) },
  { icon: 'lu-substrate-accounts', key: 'substrate', label: t('dashboard.blockchain_balances.categories.substrate'), to: route({ name: '/accounts/substrate/' }) },
  { icon: 'lu-building-2', key: 'exchange', label: t('dashboard.holdings.add.exchange'), to: route({ name: '/api-keys/exchanges/' }) },
  { icon: 'lu-landmark', key: 'bank', label: t('dashboard.holdings.add.bank'), to: route({ name: '/api-keys/banks/' }) },
  { icon: 'lu-pencil', key: 'manual', label: t('dashboard.holdings.add.manual'), to: route({ name: '/balances/manual/[[tab]]', params: { tab: 'assets' } }) },
]);

async function add(to: RouteLocationAsRelative): Promise<void> {
  await router.push({ ...to, query: { add: 'true' } });
}
</script>

<template>
  <RuiMenu
    :options="{ placement: 'bottom-start' }"
    :class-names="{ wrapper: 'w-full' }"
  >
    <template #activator="{ attrs }">
      <button
        type="button"
        class="grid grid-cols-[10px_1fr] items-center gap-2.5 w-full px-1.5 py-1 rounded text-left text-sm text-rui-text-secondary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800"
        data-testid="dashboard-add-source"
        v-bind="attrs"
      >
        <span class="size-2.5 rounded-sm border border-dashed border-rui-text-disabled" />
        <span>{{ t('dashboard.holdings.add.title') }}</span>
      </button>
    </template>
    <div class="py-2">
      <RuiButton
        v-for="option in options"
        :key="option.key"
        variant="list"
        :data-testid="`dashboard-add-source-${option.key}`"
        @click="add(option.to)"
      >
        <template #prepend>
          <RuiIcon :name="option.icon" />
        </template>
        {{ option.label }}
      </RuiButton>
    </div>
  </RuiMenu>
</template>
