<script setup lang="ts">
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

const { t } = useI18n({ useScope: 'global' });

const { useIsTaskRunning } = useTaskStore();
const isEvmAccountsDetecting = useIsTaskRunning(TaskType.DETECT_EVM_ACCOUNTS);
const { detectEvmAccounts } = useBlockchainAccountManagement();
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'right' }"
    :open-delay="400"
    tooltip-class="max-w-[16rem]"
  >
    <template #activator>
      <RuiButton
        color="primary"
        size="xl"
        :loading="isEvmAccountsDetecting"
        :disabled="isEvmAccountsDetecting"
        @click="detectEvmAccounts()"
      >
        <template #prepend>
          <RuiIcon name="lu-radar" />
        </template>
        {{ t('blockchain_balances.evm_detection.title') }}
      </RuiButton>
    </template>
    {{ t('blockchain_balances.evm_detection.tooltip') }}
  </RuiTooltip>
</template>
