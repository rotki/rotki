<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.subtitle.blockchain_address_aliases') }}
    </template>
    <EnableEnsNamesSetting />
    <AddressNamePrioritySetting />
  </SettingCategory>
</template>
