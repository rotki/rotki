<script lang="ts" setup>
import { Blockchain } from '@rotki/common';
import AccountBalancesExportImport from '@/components/accounts/AccountBalancesExportImport.vue';
import BlockchainBalanceRefreshBehaviourMenu
  from '@/components/dashboard/blockchain-balance/BlockchainBalanceRefreshBehaviourMenu.vue';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

defineProps<{
  isAccountsTabSelected: boolean;
}>();

const emit = defineEmits<{
  'refresh-click': [];
  'refresh': [];
  'add-account': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { isSectionLoading, refreshDisabled } = useBlockchainAccountLoading('evm');
const { isLoading } = useStatusStore();
const { useIsTaskRunning } = useTaskStore();

const isEth2Loading = logicOr(
  isLoading(Section.BLOCKCHAIN, Blockchain.ETH2),
  useIsTaskRunning(TaskType.FETCH_ETH2_VALIDATORS),
);
</script>

<template>
  <RuiButtonGroup
    v-if="isAccountsTabSelected"
    variant="outlined"
    color="primary"
  >
    <RuiButton
      :disabled="refreshDisabled"
      :loading="isSectionLoading"
      @click="emit('refresh-click')"
    >
      <template #prepend>
        <RuiIcon name="lu-refresh-ccw" />
      </template>
      {{ t('common.refresh') }}
    </RuiButton>
    <RuiMenu>
      <template #activator="{ attrs }">
        <RuiButton
          v-bind="{
            ...attrs,
            'data-cy': 'blockchain-account-refresh',
          }"
          color="primary"
          variant="outlined"
          class="!outline-0 px-2"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>

      <BlockchainBalanceRefreshBehaviourMenu />
    </RuiMenu>
  </RuiButtonGroup>

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

  <RuiButton
    data-cy="add-blockchain-account"
    color="primary"
    @click="emit('add-account')"
  >
    <template #prepend>
      <RuiIcon name="lu-plus" />
    </template>
    {{ t('blockchain_balances.add_account') }}
  </RuiButton>

  <AccountBalancesExportImport />
</template>
