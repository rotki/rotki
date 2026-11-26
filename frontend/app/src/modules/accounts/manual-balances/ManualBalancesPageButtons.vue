<script setup lang="ts">
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import ManualBalancesRefreshButton from '@/modules/accounts/manual-balances/ManualBalancesRefreshButton.vue';
import HideSmallBalances from '@/modules/settings/HideSmallBalances.vue';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const emit = defineEmits<{
  add: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { useIsActive } = useTaskCenter();
const loading = useIsActive(ActivityKind.MANUAL_BALANCES);
</script>

<template>
  <ManualBalancesRefreshButton />
  <RuiButton
    color="primary"
    data-testid="manual-balances-add-button"
    :disabled="loading"
    @click="emit('add')"
  >
    <template #prepend>
      <RuiIcon name="lu-plus" />
    </template>
    {{ t('manual_balances.add_manual_balance') }}
  </RuiButton>
  <HideSmallBalances :source="BalanceSource.MANUAL" />
</template>
