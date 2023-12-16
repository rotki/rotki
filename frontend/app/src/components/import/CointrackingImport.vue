<script setup lang="ts">
import { Routes } from '@/router/routes';

const { t } = useI18n();
</script>

<template>
  <ImportSource source="cointracking">
    <template #hint>
      {{ t('import_data.cointracking.preferred') }}
    </template>
    <i18n-t
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.cointracking.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.cointracking.line_one') }}</li>
      <li>{{ t('import_data.cointracking.line_two') }}</li>
      <i18n-t
        keypath="import_data.cointracking.line_three"
        tag="span"
      >
        <InternalLink :to="Routes.ACCOUNTS_BALANCES">
          {{ t('import_data.cointracking.link') }}
        </InternalLink>
      </i18n-t>
    </ul>
  </ImportSource>
</template>
