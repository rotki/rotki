<script setup lang="ts">
import { TaskType } from '@/types/task-type';

const { isTaskRunning } = useTaskStore();
const isEvmAccountsDetecting = isTaskRunning(TaskType.DETECT_EVM_ACCOUNTS);
const { detectEvmAccounts } = useBlockchains();

const { tc } = useI18n();
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
        {{ tc('blockchain_balances.evm_detection.title') }}
      </v-btn>
    </template>
    <span>
      {{ tc('blockchain_balances.evm_detection.tooltip') }}
    </span>
  </v-tooltip>
</template>
