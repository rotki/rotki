<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import ImportNotes from '@/modules/user-data/ImportNotes.vue';
import ImportSource from '@/modules/user-data/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
    <div class="flex flex-col gap-4">
      <ImportSource source="rotki_events">
        <template #upload-title>
          <strong>
            {{ t('import_data.custom.import_events') }}
          </strong>
        </template>
      </ImportSource>
      <ImportSource source="rotki_trades">
        <template #upload-title>
          <strong>
            {{ t('import_data.custom.import_trades') }}
          </strong>
        </template>
      </ImportSource>
    </div>

    <ImportNotes :caveat="false">
      <i18n-t
        scope="global"
        tag="p"
        keypath="import_data.custom.migration_assistant"
        class="m-0"
      >
        <template #link>
          <ExternalLink
            color="primary"
            :url="externalLinks.migrationAssistant"
          >
            {{ t('import_data.custom.migration_assistant_link') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </ImportNotes>
  </div>
</template>
