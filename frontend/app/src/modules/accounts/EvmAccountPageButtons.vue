<script lang="ts" setup>
import { Blockchain } from '@rotki/common';
import AccountBalancesExportImport from '@/modules/accounts/AccountBalancesExportImport.vue';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import BlockchainBalanceRefreshBehaviourMenu
  from '@/modules/balances/BlockchainBalanceRefreshBehaviourMenu.vue';
import { Section } from '@/modules/core/common/status';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useSectionStatus } from '@/modules/shell/sync-progress/use-section-status';

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

const { isSectionLoading, refreshDisabled } = useBlockchainAccountLoading('evm');
const { useIsTaskRunning } = useTaskStore();
const { isLoading: eth2Loading } = useSectionStatus(Section.BLOCKCHAIN, Blockchain.ETH2);

const isEth2Loading = logicOr(
  eth2Loading,
  useIsTaskRunning(TaskType.FETCH_ETH2_VALIDATORS),
);
</script>

<template>
  <RuiButtonGroup
    v-if="isAccountsTabSelected"
    variant="outlined"
    color="primary"
    size="lg"
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
          size="lg"
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
    size="lg"
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
        data-cy="add-blockchain-account"
        color="primary"
        size="lg"
        :disabled="addDisabled"
        @click="emit('add-account')"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('blockchain_balances.add_account') }}
      </RuiButton>
    </template>
    {{ t('blockchain_balances.add_validator_premium') }}
  </RuiTooltip>

  <AccountBalancesExportImport />
</template>
