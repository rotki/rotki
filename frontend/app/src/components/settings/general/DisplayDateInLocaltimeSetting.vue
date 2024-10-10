<script setup lang="ts">
const displayDateInLocaltime = ref<boolean>(true);
const { displayDateInLocaltime: enabled } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(displayDateInLocaltime, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    setting="displayDateInLocaltime"
    :error-message="t('general_settings.display_date_in_localtime.validation.error')"
  >
    <template #title>
      {{ t('general_settings.display_date_in_localtime.title') }}
    </template>
    <template
      #default="{ error, success, updateImmediate }"
    >
      <RuiSwitch
        v-model="displayDateInLocaltime"
        class="general-settings__fields__display-date-in-localtime"
        color="primary"
        :label="t('general_settings.display_date_in_localtime.label')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </template>
  </SettingsOption>
</template>
