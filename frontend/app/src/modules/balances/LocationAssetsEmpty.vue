<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';
import { addAccountLink } from '@/modules/accounts/add-account-link';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { ChainType } from '@/modules/core/api/types/chains';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';

const { identifier, name } = defineProps<{
  identifier: string;
  name: string;
}>();

interface EmptyAction {
  readonly description: string;
  readonly icon: RuiIcons;
  readonly label: string;
  readonly to: RouteLocationRaw;
}

const { t } = useI18n({ useScope: 'global' });

const { allExchanges } = storeToRefs(useLocationStore());
const { bankBalanceLocations: banks } = storeToRefs(useBankConnectionsStore());
const { getChainAccountType, matchChain } = useSupportedChains();

/** Where balances for this kind of location come from, and the page that adds one. */
const action = computed<EmptyAction>(() => {
  const chain = matchChain(identifier);
  if (chain) {
    const category = getChainAccountType(chain) ?? ChainType.EVM;
    return {
      description: t('locations.empty.chain', { name }),
      icon: 'lu-wallet',
      label: t('locations.empty.add_account'),
      to: category === ChainType.EVM
        ? addAccountLink({ addresses: [], chain })
        : { path: `/accounts/${category}`, query: { add: 'true' } },
    };
  }

  if (get(banks).includes(identifier)) {
    return {
      description: t('locations.empty.bank', { name }),
      icon: 'lu-landmark',
      label: t('locations.empty.connect', { name }),
      to: { path: '/api-keys/banks', query: { add: 'true', location: identifier } },
    };
  }

  if (get(allExchanges).includes(identifier)) {
    return {
      description: t('locations.empty.exchange', { name }),
      icon: 'lu-coins-exchange',
      label: t('locations.empty.connect', { name }),
      to: { path: '/api-keys/exchanges', query: { add: 'true', location: identifier } },
    };
  }

  return {
    description: t('locations.empty.manual', { name }),
    icon: 'lu-pencil',
    label: t('locations.empty.add_manual'),
    to: { name: '/balances/manual/[[tab]]', params: { tab: 'assets' }, query: { add: 'true' } },
  };
});
</script>

<template>
  <div
    class="rounded-rui-card border border-rui-divider bg-rui-surface pb-10"
    data-testid="location-assets-empty"
  >
    <TableEmptyNotice
      :icon="action.icon"
      :title="t('locations.empty.title', { name })"
      :description="action.description"
    >
      <RouterLink :to="action.to">
        <RuiButton
          color="primary"
          data-testid="location-assets-empty-action"
        >
          <template #prepend>
            <RuiIcon name="lu-plus" />
          </template>
          {{ action.label }}
        </RuiButton>
      </RouterLink>
    </TableEmptyNotice>
  </div>
</template>
