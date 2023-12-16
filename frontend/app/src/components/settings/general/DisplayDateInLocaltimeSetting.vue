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
    #default="{ error, success, updateImmediate }"
    setting="displayDateInLocaltime"
    :error-message="t('general_settings.validation.display_date_in_localtime.error')"
  >
    <RuiSwitch
      v-model="displayDateInLocaltime"
      class="general-settings__fields__display-date-in-localtime"
      color="primary"
      :label="t('general_settings.labels.display_date_in_localtime')"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
