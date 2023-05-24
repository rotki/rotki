<script setup lang="ts">
import { TaskType } from '@/types/task-type';

const { isTaskRunning } = useTaskStore();
const isEvmAccountsDetecting = isTaskRunning(TaskType.DETECT_EVM_ACCOUNTS);
const { detectEvmAccounts } = useBlockchains();

const { t } = useI18n();
</script>

<template>
  <v-tooltip right max-width="300">
    <template #activator="{ on }">
      <v-btn
        color="primary"
        depressed
        :loading="isEvmAccountsDetecting"
        :disabled="isEvmAccountsDetecting"
        v-on="on"
        @click="detectEvmAccounts()"
      >
        {{ t('blockchain_balances.evm_detection.title') }}
      </v-btn>
    </template>
    <span>
      {{ t('blockchain_balances.evm_detection.tooltip') }}
    </span>
  </v-tooltip>
</template>
