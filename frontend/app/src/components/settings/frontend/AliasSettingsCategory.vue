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
      class="mb-4"
    >
      {{ t('address_book.hint.priority.title') }}
    </RuiAlert>

    <RuiCard
      rounded="md"
      no-padding
      class="overflow-hidden"
    >
      <div class="p-4 border-b border-default">
        <EnableEnsNamesSetting />
      </div>
      <div class="p-4">
        <AddressNamePrioritySetting />
      </div>
    </RuiCard>
  </SettingCategory>
</template>
