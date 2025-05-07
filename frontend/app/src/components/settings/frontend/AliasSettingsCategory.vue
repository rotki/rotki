<script setup lang="ts">
import AddressNamePrioritySetting from '@/components/settings/frontend/AddressNamePrioritySetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.subtitle.blockchain_address_aliases') }}
    </template>
    <RuiAlert
      type="info"
      class="my-4"
    >
      {{ t('frontend_settings.alias_names.title') }}
    </RuiAlert>
    <AddressNamePrioritySetting />
  </SettingCategory>
</template>
