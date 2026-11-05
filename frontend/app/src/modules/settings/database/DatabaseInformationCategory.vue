<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import DatabaseInformation from '@/modules/settings/database/DatabaseInformation.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
defineProps<
  /* @vue-ignore */ HTMLAttributes
>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('database_settings.database_info.title') }}
    </template>
    <DatabaseInformation />
  </SettingCategory>
</template>
