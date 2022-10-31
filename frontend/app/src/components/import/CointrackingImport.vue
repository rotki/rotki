<template>
  <import-source source="cointracking">
    <template #hint>
      {{ t('import_data.cointracking.preferred') }}
    </template>
    <i18n tag="span" path="import_data.cointracking.note">
      <strong>{{ t('import_data.cointracking.source_name') }}</strong>
    </i18n>
    <ul>
      <li>{{ t('import_data.cointracking.line_one') }}</li>
      <li>{{ t('import_data.cointracking.line_two') }}</li>
      <i18n path="import_data.cointracking.line_three">
        <router-link to="/accounts-balance">
          {{ t('import_data.cointracking.link') }}
        </router-link>
      </i18n>
    </ul>
  </import-source>
</template>
<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n();
</script>
