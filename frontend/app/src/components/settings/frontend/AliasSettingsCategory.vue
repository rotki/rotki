<script setup lang="ts">
const { t } = useI18n();
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
