<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  name: 'import',
  meta: {
    noteLocation: NoteLocation.IMPORT,
  },
});

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
      <i18n-t
        tag="span"
        keypath="import_data.notice"
      >
        <template #link>
          <ExternalLink
            color="primary"
            :url="externalLinks.githubNewIssue"
          >
            {{ t('import_data.notice_link') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </RuiAlert>

    <GroupedImport />
  </TablePageLayout>
</template>
