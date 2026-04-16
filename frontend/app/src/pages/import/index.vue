<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { NoteLocation } from '@/modules/core/common/notes';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import GroupedImport from '@/modules/user-data/GroupedImport.vue';

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
