<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { NoteLocation } from '@/types/notes';
import GroupedImport from '@/components/import/GroupedImport.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.IMPORT,
  },
  name: 'import',
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
