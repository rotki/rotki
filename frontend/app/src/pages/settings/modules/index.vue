<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div>
    <Card>
      <template #title>{{ t('module_settings.title') }}</template>
      <div class="text-h6" v-text="t('module_settings.active_modules')" />
      <p
        class="text--secondary"
        v-text="t('module_settings.active_modules_description')"
      />
      <ModuleSelector class="mt-6" />
      <div class="mt-6 text-h6" v-text="t('module_settings.select_accounts')" />
      <p
        class="text--secondary"
        v-text="t('module_settings.select_accounts_description')"
      />
      <ModuleAddressSelector />
      <span class="text-caption" v-text="t('module_settings.hint')" />
    </Card>
  </div>
</template>
