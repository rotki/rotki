<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import Explorers from '@/modules/settings/explorers/Explorers.vue';
import AddressNamePrioritySetting from '@/modules/settings/frontend/AddressNamePrioritySetting.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
defineProps<
  /* @vue-ignore */ HTMLAttributes
>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.sections.addresses') }}
    </template>
    <SettingsItem>
      <template #title>
        {{ t('frontend_settings.alias_names.row_title') }}
      </template>
      <template #subtitle>
        {{ t('frontend_settings.alias_names.title') }}
      </template>
      <AddressNamePrioritySetting />
    </SettingsItem>
    <Explorers />
  </SettingCategory>
</template>
