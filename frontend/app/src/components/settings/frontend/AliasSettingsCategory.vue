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
      class="my-1"
    >
      {{ t('address_book.hint.priority.title') }}
    </RuiAlert>
    <RuiCard
      rounded="md"
      :no-padding="true"
      class="overflow-hidden"
    >
      <div class="pl-8 pt-2">
        <EnableEnsNamesSetting />
      </div>
      <AddressNamePrioritySetting />
    </RuiCard>
  </SettingCategory>
</template>
