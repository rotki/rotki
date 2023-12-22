<script setup lang="ts">
import { externalLinks } from '@/data/external-links';

const { t } = useI18n();
</script>

<template>
  <TablePageLayout :title="[t('import_data.title')]">
    <template #buttons>
      <HintMenuIcon left>
        {{ t('import_data.description') }}
      </HintMenuIcon>
    </template>

    <RuiAlert
      variant="outlined"
      type="warning"
      :title="t('import_data.notice_warning')"
    >
      <i18n tag="span" path="import_data.notice">
        <template #link>
          <ExternalLink color="primary" :url="externalLinks.githubNewIssue">
            {{ t('import_data.notice_link') }}
          </ExternalLink>
        </template>
      </i18n>
    </RuiAlert>

    <GroupedImport />
  </TablePageLayout>
</template>
