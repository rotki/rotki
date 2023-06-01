<script setup lang="ts">
import { Routes } from '@/router/routes';

const { t } = useI18n();
</script>

<template>
  <import-source source="cryptocom">
    <i18n tag="span" path="import_data.note">
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
          <internal-link :to="Routes.ACCOUNTS_BALANCES_MANUAL">
            {{ t('import_data.cryptocom.line_four_link') }}
          </internal-link>
        </i18n>
      </li>
    </ul>
  </import-source>
</template>
