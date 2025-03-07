<script setup lang="ts">
import InternalLink from '@/components/helper/InternalLink.vue';
import ImportSource from '@/components/import/ImportSource.vue';
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
        <InternalLink :to="Routes.ACCOUNTS">
          {{ t('navigation_menu.accounts') }}
        </InternalLink>
      </i18n-t>
    </ul>
  </ImportSource>
</template>
