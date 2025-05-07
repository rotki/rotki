<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
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
      <div class="text-rui-text-secondary">
        {{ t('import_data.bittrex.warning') }}
      </div>
    </ImportSource>
  </div>
</template>
