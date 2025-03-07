<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ImportSource from '@/components/import/ImportSource.vue';
import { externalLinks } from '@shared/external-links';

const { t } = useI18n();
</script>

<template>
  <ImportSource source="binance">
    <i18n-t
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.binance.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.binance.line_one') }}</li>
      <li>
        <i18n-t
          keypath="import_data.binance.line_two"
          tag="span"
        >
          <template #link>
            <ExternalLink
              :text="t('import_data.binance.name')"
              :url="externalLinks.binanceCsvExport"
              color="primary"
            />
          </template>
        </i18n-t>
      </li>
      <li>{{ t('import_data.binance.line_three') }}</li>
    </ul>
  </ImportSource>
</template>
