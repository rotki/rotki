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
import { storeToRefs } from 'pinia';
import { supportedLanguages } from '@/data/supported-language';
import { useFrontendSettingsStore } from '@/store/settings';
import { SupportedLanguage } from '@/types/frontend-settings';

const language = ref<string>(SupportedLanguage.EN);
const { language: currentLanguage } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(language, get(currentLanguage));
});
</script>
