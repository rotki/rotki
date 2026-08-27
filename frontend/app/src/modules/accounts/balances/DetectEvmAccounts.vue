<script setup lang="ts">
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const { t } = useI18n({ useScope: 'global' });

const { useIsActive } = useTaskCenter();
const isEvmAccountsDetecting = useIsActive(ActivityKind.ACCOUNTS, ActivityPart.DETECT);
const { detectEvmAccounts } = useBlockchainAccountManagement();
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'right' }"
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
