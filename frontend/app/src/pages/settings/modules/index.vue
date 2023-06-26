<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div>
    <card>
      <template #title>{{ t('module_settings.title') }}</template>
      <div class="text-h6" v-text="t('module_settings.active_modules')" />
      <p
        class="text--secondary"
        v-text="t('module_settings.active_modules_description')"
      />
      <module-selector class="mt-6" />
      <div class="mt-6 text-h6" v-text="t('module_settings.select_accounts')" />
      <p
        class="text--secondary"
        v-text="t('module_settings.select_accounts_description')"
      />
      <module-address-selector />
      <span class="text-caption" v-text="t('module_settings.hint')" />
    </card>
  </div>
</template>
