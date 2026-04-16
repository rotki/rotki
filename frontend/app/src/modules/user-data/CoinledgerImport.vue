<script setup lang="ts">
import ImportSource from '@/modules/user-data/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="coinledger">
    <i18n-t
      scope="global"
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.coinledger.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.coinledger.line_one') }}</li>
    </ul>
  </ImportSource>
</template>
