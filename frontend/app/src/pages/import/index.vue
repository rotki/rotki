<template>
  <v-container>
    <card-title class="mt-2">{{ t('import_data.title') }}</card-title>
    <v-row class="mt-4" no-gutters>
      <v-col cols="12">
        {{ t('import_data.description') }}
      </v-col>
      <v-col cols="12">
        <v-alert outlined class="mt-2">
          <i18n tag="span" path="import_data.notice">
            <template #warning>
              <strong> {{ t('import_data.notice_warning') }}</strong>
            </template>
            <template #link>
              <external-link
                url="https://github.com/rotki/rotki/issues/new/choose"
              >
                {{ t('import_data.notice_link') }}
              </external-link>
            </template>
          </i18n>
        </v-alert>
      </v-col>
    </v-row>

    <grouped-import class="mt-4" />
  </v-container>
</template>

<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import GroupedImport from '@/components/import/GroupedImport.vue';

const { t } = useI18n();
</script>
