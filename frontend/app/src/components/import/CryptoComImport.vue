<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import InternalLink from '@/components/helper/InternalLink.vue';
import ImportSource from '@/components/import/ImportSource.vue';
import { Routes } from '@/router/routes';
import { externalLinks } from '@shared/external-links';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="cryptocom">
    <i18n-t
      scope="global"
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.cryptocom.source_name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>
        <i18n-t
          scope="global"
          tag="span"
          keypath="import_data.cryptocom.line_one"
        >
          <ExternalLink
            color="primary"
            :url="externalLinks.githubNewIssue"
          >
            {{ t('import_data.cryptocom.line_one_link') }}
          </ExternalLink>
        </i18n-t>
      </li>
      <li>
        <i18n-t
          scope="global"
          tag="span"
          keypath="import_data.cryptocom.line_two"
        >
          <strong>{{ t('import_data.cryptocom.line_two_warning') }}</strong>
        </i18n-t>
      </li>
      <li>{{ t('import_data.cryptocom.line_three') }}</li>
      <li>
        <i18n-t
          scope="global"
          keypath="import_data.cryptocom.line_four"
          tag="span"
        >
          <InternalLink :to="Routes.BALANCES_MANUAL">
            {{ t('navigation_menu.balances_sub.manual_balances') }}
          </InternalLink>
        </i18n-t>
      </li>
    </ul>
  </ImportSource>
</template>
