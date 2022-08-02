<template>
  <settings-option
    #default="{ error, success, update }"
    setting="language"
    frontend-setting
    :error-message="$t('general_settings.validation.language.error')"
  >
    <v-select
      v-model="language"
      :items="supportedLanguages"
      item-text="label"
      item-value="identifier"
      outlined
      :label="$t('general_settings.labels.language')"
      persistent-hint
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';
import { supportedLanguages } from '@/data/supported-language';
import { SupportedLanguage } from '@/types/frontend-settings';

const language = ref<string>(SupportedLanguage.EN);
const { frontendSettings } = useSettings();

onMounted(() => {
  const settings = get(frontendSettings);
  set(language, settings.language);
});
</script>
