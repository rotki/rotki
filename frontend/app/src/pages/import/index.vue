<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <VContainer>
    <CardTitle class="mt-2">{{ t('import_data.title') }}</CardTitle>
    <div class="text-rui-text-secondary">
      {{ t('import_data.description') }}
    </div>
    <RuiAlert
      outlined
      type="warning"
      class="mt-4"
      :title="t('import_data.notice_warning')"
    >
      <i18n tag="span" path="import_data.notice">
        <template #link>
          <ExternalLink url="https://github.com/rotki/rotki/issues/new/choose">
            {{ t('import_data.notice_link') }}
          </ExternalLink>
        </template>
      </i18n>
    </RuiAlert>

    <GroupedImport class="mt-8" />
  </VContainer>
</template>
