<script setup lang="ts">
import { RuiButton, RuiButtonGroup } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { AccountHistoryRange } from '@/modules/balances/account-history/account-history-selection';

const range = defineModel<AccountHistoryRange>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const ranges = computed<{ value: AccountHistoryRange; label: string }[]>(() => [
  { label: t('account_history.range.month'), value: AccountHistoryRange.MONTH },
  { label: t('account_history.range.quarter'), value: AccountHistoryRange.QUARTER },
  { label: t('account_history.range.half_year'), value: AccountHistoryRange.HALF_YEAR },
  { label: t('account_history.range.year'), value: AccountHistoryRange.YEAR },
  { label: t('account_history.range.all'), value: AccountHistoryRange.ALL },
]);
</script>

<template>
  <RuiButtonGroup
    v-model="range"
    variant="segmented"
    required
    size="sm"
    data-testid="account-history-range"
  >
    <RuiButton
      v-for="option in ranges"
      :key="option.value"
      :model-value="option.value"
      :data-testid="`account-history-range-${option.value}`"
    >
      {{ option.label }}
    </RuiButton>
  </RuiButtonGroup>
</template>
