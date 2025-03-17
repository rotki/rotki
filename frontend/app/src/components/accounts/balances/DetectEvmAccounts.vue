<script setup lang="ts">
import { useBlockchains } from '@/composables/blockchain';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const { useIsTaskRunning } = useTaskStore();
const isEvmAccountsDetecting = useIsTaskRunning(TaskType.DETECT_EVM_ACCOUNTS);
const { detectEvmAccounts } = useBlockchains();

const { t } = useI18n();
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'right' }"
    :open-delay="400"
    tooltip-class="max-w-[16rem]"
  >
    <template #activator>
      <RuiButton
        class="py-2"
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
