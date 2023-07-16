<script setup lang="ts">
const displayDateInLocaltime = ref<boolean>(true);
const { displayDateInLocaltime: enabled } = storeToRefs(
  useGeneralSettingsStore()
);

onMounted(() => {
  set(displayDateInLocaltime, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="displayDateInLocaltime"
    :error-message="
      t('general_settings.validation.display_date_in_localtime.error')
    "
  >
    <VSwitch
      v-model="displayDateInLocaltime"
      class="general-settings__fields__display-date-in-localtime mb-4 mt-0"
      color="primary"
      :label="t('general_settings.labels.display_date_in_localtime')"
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </SettingsOption>
</template>
