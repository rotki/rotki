<script setup lang="ts">
import { externalLinks } from '@/data/external-links';

const { t } = useI18n();
</script>

<template>
  <ImportSource source="binance">
    <i18n
      tag="span"
      path="import_data.note"
    >
      <strong>{{ t('import_data.binance.name') }}</strong>
    </i18n>
    <ul class="list-disc">
      <li>{{ t('import_data.binance.line_one') }}</li>
      <li>
        <i18n path="import_data.binance.line_two">
          <template #link>
            <ExternalLink
              :text="t('import_data.binance.name')"
              :url="externalLinks.binanceCsvExport"
              color="primary"
            />
          </template>
        </i18n>
      </li>
      <li>{{ t('import_data.binance.line_three') }}</li>
    </ul>
  </ImportSource>
</template>
