<script setup lang="ts">
import { Routes } from '@/router/routes';

const { t } = useI18n();
</script>

<template>
  <ImportSource source="cryptocom">
    <i18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.cryptocom.source_name') }}</strong>
    </i18n>
    <ul class="list-disc">
      <li>
        <i18n tag="span" path="import_data.cryptocom.line_one">
          <ExternalLink
            color="primary"
            url="https://github.com/rotki/rotki/issues/new/choose"
          >
            {{ t('import_data.cryptocom.line_one_link') }}
          </ExternalLink>
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
          <InternalLink :to="Routes.ACCOUNTS_BALANCES_MANUAL">
            {{ t('import_data.cryptocom.line_four_link') }}
          </InternalLink>
        </i18n>
      </li>
    </ul>
  </ImportSource>
</template>
