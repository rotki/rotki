<script setup lang="ts">
import { TaskType } from '@/types/task-type';

const { isTaskRunning } = useTaskStore();
const isEvmAccountsDetecting = isTaskRunning(TaskType.DETECT_EVM_ACCOUNTS);
const { detectEvmAccounts } = useBlockchains();

const { t } = useI18n();
</script>

<template>
  <RuiTooltip :popper="{ placement: 'right' }" max-width="300">
    <template #activator>
      <RuiButton
        color="primary"
        :loading="isEvmAccountsDetecting"
        :disabled="isEvmAccountsDetecting"
        @click="detectEvmAccounts()"
      >
        {{ t('blockchain_balances.evm_detection.title') }}
      </RuiButton>
    </template>
    {{ t('blockchain_balances.evm_detection.tooltip') }}
  </RuiTooltip>
</template>
