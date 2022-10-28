<template>
  <import-source source="cryptocom">
    <i18n tag="span" path="import_data.cryptocom.note">
      <strong>{{ t('import_data.cryptocom.source_name') }}</strong>
    </i18n>
    <ul>
      <li>
        <i18n tag="span" path="import_data.cryptocom.line_one">
          <external-link url="https://github.com/rotki/rotki/issues/new/choose">
            {{ t('import_data.cryptocom.line_one_link') }}
          </external-link>
        </i18n>
      </li>
      <li>
        <i18n tag="span" path="import_data.cryptocom.line_two">
          <strong>{{ t('import_data.cryptocom.line_two_warning') }}</strong>
        </i18n>
      </li>
      <li>{{ t('import_data.cryptocom.line_three') }}</li>
      <li>
        <i18n path="import_data.cryptocom.line_four" tag="span">
          <router-link to="/accounts-balance/manual-balances">
            {{ t('import_data.cryptocom.line_four_link') }}
          </router-link>
        </i18n>
      </li>
    </ul>
  </import-source>
</template>
<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n();
</script>
