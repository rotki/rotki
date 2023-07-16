<script setup lang="ts">
import { Routes } from '@/router/routes';

const { t } = useI18n();
</script>

<template>
  <ImportSource source="cryptocom">
    <I18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.cryptocom.source_name') }}</strong>
    </I18n>
    <ul>
      <li>
        <I18n tag="span" path="import_data.cryptocom.line_one">
          <ExternalLink url="https://github.com/rotki/rotki/issues/new/choose">
            {{ t('import_data.cryptocom.line_one_link') }}
          </ExternalLink>
        </I18n>
      </li>
      <li>
        <I18n tag="span" path="import_data.cryptocom.line_two">
          <strong>{{ t('import_data.cryptocom.line_two_warning') }}</strong>
        </I18n>
      </li>
      <li>{{ t('import_data.cryptocom.line_three') }}</li>
      <li>
        <I18n path="import_data.cryptocom.line_four" tag="span">
          <InternalLink :to="Routes.ACCOUNTS_BALANCES_MANUAL">
            {{ t('import_data.cryptocom.line_four_link') }}
          </InternalLink>
        </I18n>
      </li>
    </ul>
  </ImportSource>
</template>
