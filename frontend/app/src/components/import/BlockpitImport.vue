<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="blockpit">
    <i18n-t
      scope="global"
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.blockpit.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.blockpit.line_one') }}</li>
    </ul>
  </ImportSource>
</template>
