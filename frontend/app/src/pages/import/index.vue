<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import GroupedImport from '@/components/import/GroupedImport.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { NoteLocation } from '@/types/notes';
import { externalLinks } from '@shared/external-links';

definePage({
  meta: {
    noteLocation: NoteLocation.IMPORT,
  },
  name: 'import',
});

const { t } = useI18n({ useScope: 'global' });
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
        scope="global"
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
