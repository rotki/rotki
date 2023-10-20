<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div class="p-4">
    <TablePageLayout :title="[t('import_data.title')]">
      <template #buttons>
        <HintMenuIcon>
          {{ t('import_data.description') }}
        </HintMenuIcon>
      </template>

      <RuiAlert
        outlined
        type="warning"
        :title="t('import_data.notice_warning')"
      >
        <i18n tag="span" path="import_data.notice">
          <template #link>
            <ExternalLink
              url="https://github.com/rotki/rotki/issues/new/choose"
            >
              {{ t('import_data.notice_link') }}
            </ExternalLink>
          </template>
        </i18n>
      </RuiAlert>

      <GroupedImport />
    </TablePageLayout>
  </div>
</template>
