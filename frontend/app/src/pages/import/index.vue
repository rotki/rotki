<script setup lang="ts">
import { externalLinks } from '@/data/external-links';

const { t } = useI18n();
</script>

<template>
  <TablePageLayout :title="[t('import_data.title')]">
    <template #buttons>
      <HintMenuIcon :popper="{ placement: 'left-start' }">
        {{ t('import_data.description') }}
      </HintMenuIcon>
    </template>

    <RuiAlert
      type="warning"
      :title="t('common.important_notice')"
    >
      <i18n
        tag="span"
        path="import_data.notice"
      >
        <template #link>
          <ExternalLink
            color="primary"
            :url="externalLinks.githubNewIssue"
          >
            {{ t('import_data.notice_link') }}
          </ExternalLink>
        </template>
      </i18n>
    </RuiAlert>

    <GroupedImport />
  </TablePageLayout>
</template>
