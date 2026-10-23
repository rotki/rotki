<script lang="ts" setup>
import { Blockchain } from '@rotki/common';
import AccountBalancesExportImport from '@/modules/accounts/AccountBalancesExportImport.vue';
import AccountsRefreshButton from '@/modules/accounts/AccountsRefreshButton.vue';
import EvmAccountsRefreshMenu from '@/modules/accounts/EvmAccountsRefreshMenu.vue';
import { chainBalancesActivity } from '@/modules/balances/balances.activity';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { validatorsActivity } from '@/modules/staking/staking.activity';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const { addDisabled = false } = defineProps<{
  isAccountsTabSelected: boolean;
  addDisabled?: boolean;
}>();

const emit = defineEmits<{
  'refresh-click': [];
  'refresh': [];
  'add-account': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { useIsActive, useIsActivePrefix } = useTaskCenter();
const eth2Querying = useIsActivePrefix(chainBalancesActivity.kind, ...chainBalancesActivity.partsWithin([Blockchain.ETH2]));
const eth2Hydrating = useBalanceRefreshState().useIsHydrating(Blockchain.ETH2);
const eth2Loading = logicOr(eth2Querying, eth2Hydrating);

const isEth2Loading = logicOr(
  eth2Loading,
  useIsActive(validatorsActivity.kind, ...validatorsActivity.partsOf()),
);
</script>

<template>
  <AccountsRefreshButton
    v-if="isAccountsTabSelected"
    category="evm"
    @refresh="emit('refresh-click')"
  >
    <template #menu="{ close }">
      <EvmAccountsRefreshMenu @close="close()" />
    </template>
  </AccountsRefreshButton>

  <RuiButton
    v-else
    color="primary"
    variant="outlined"
    :loading="isEth2Loading"
    @click="emit('refresh')"
  >
    <template #prepend>
      <RuiIcon name="lu-refresh-ccw" />
    </template>
    {{ t('common.refresh') }}
  </RuiButton>

  <RuiTooltip
    :disabled="!addDisabled"
    :open-delay="300"
  >
    <template #activator>
      <RuiButton
        data-testid="add-blockchain-account"
        color="primary"
        :disabled="addDisabled"
        @click="emit('add-account')"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ isAccountsTabSelected ? t('blockchain_balances.add_evm_account') : t('blockchain_balances.add_account') }}
      </RuiButton>
    </template>
    {{ t('blockchain_balances.add_validator_premium') }}
  </RuiTooltip>

  <AccountBalancesExportImport />
</template>
