<script setup lang="ts">
const zeroBased = ref<boolean>(false);
const { graphZeroBased: enabled } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(zeroBased, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <settings-option
    #default="{ error, success, update }"
    setting="graphZeroBased"
    frontend-setting
  >
    <v-switch
      v-model="zeroBased"
      class="general-settings__fields__zero-base mb-4 mt-2"
      :label="t('frontend_settings.label.zero_based')"
      :hint="t('frontend_settings.label.zero_based_hint')"
      persistent-hint
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </settings-option>
</template>
