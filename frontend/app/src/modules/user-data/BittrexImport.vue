<script setup lang="ts">
import ImportSource from '@/modules/user-data/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="bittrex">
    <template #upload-title>
      <i18n-t
        scope="global"
        tag="span"
        keypath="import_data.bittrex.import"
      >
        <strong>{{ t('import_data.bittrex.import_types') }}</strong>
      </i18n-t>
    </template>
    <ul>
      <li>{{ t('import_data.bittrex.warning') }}</li>
    </ul>
  </ImportSource>
</template>
