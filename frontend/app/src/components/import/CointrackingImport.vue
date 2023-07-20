<script setup lang="ts">
import { Routes } from '@/router/routes';

const { t } = useI18n();
</script>

<template>
  <ImportSource source="cointracking">
    <template #hint>
      {{ t('import_data.cointracking.preferred') }}
    </template>
    <i18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.cointracking.name') }}</strong>
    </i18n>
    <ul>
      <li>{{ t('import_data.cointracking.line_one') }}</li>
      <li>{{ t('import_data.cointracking.line_two') }}</li>
      <i18n path="import_data.cointracking.line_three">
        <InternalLink :to="Routes.ACCOUNTS_BALANCES">
          {{ t('import_data.cointracking.link') }}
        </InternalLink>
      </i18n>
    </ul>
  </ImportSource>
</template>
