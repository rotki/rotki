<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <VContainer>
    <CardTitle class="mt-2">{{ t('import_data.title') }}</CardTitle>
    <VRow class="mt-4" no-gutters>
      <VCol cols="12">
        {{ t('import_data.description') }}
      </VCol>
      <VCol cols="12">
        <VAlert outlined class="mt-2">
          <I18n tag="span" path="import_data.notice">
            <template #warning>
              <strong> {{ t('import_data.notice_warning') }}</strong>
            </template>
            <template #link>
              <ExternalLink
                url="https://github.com/rotki/rotki/issues/new/choose"
              >
                {{ t('import_data.notice_link') }}
              </ExternalLink>
            </template>
          </I18n>
        </VAlert>
      </VCol>
    </VRow>

    <GroupedImport class="mt-4" />
  </VContainer>
</template>
