<template>
  <settings-option
    #default="{ error, success, update }"
    setting="language"
    frontend-setting
    :error-message="t('general_settings.validation.language.error')"
  >
    <v-select
      v-model="language"
      :items="supportedLanguages"
      item-text="label"
      item-value="identifier"
      outlined
      hide-details
      :dense="dense"
      :label="rootAttrs.label ?? t('general_settings.labels.language')"
      persistent-hint
      :success-messages="success"
      :error-messages="error"
      v-bind="rootAttrs"
      @change="update"
    >
      <template #item="{ item }">
        <language-selector-item
          :dense="dense"
          :show-label="showLabel"
          :countries="item.countries ?? [item.identifier]"
          :label="item.label"
        />
      </template>
      <template #selection="{ item }">
        <language-selector-item
          :dense="dense"
          :show-label="showLabel"
          :countries="item.countries ?? [item.identifier]"
          :label="item.label"
        />
      </template>
    </v-select>
  </settings-option>
</template>

<script setup lang="ts">
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, ref, useAttrs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import LanguageSelectorItem from '@/components/settings/general/language/LanguageSelectorItem.vue';
import { supportedLanguages } from '@/data/supported-language';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { SupportedLanguage } from '@/types/frontend-settings';

defineProps({
  dense: {
    required: false,
    type: Boolean,
    default: false
  },
  showLabel: {
    required: false,
    type: Boolean,
    default: true
  }
});
const language = ref<string>(SupportedLanguage.EN);
const { language: currentLanguage } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(language, get(currentLanguage));
});

const { t } = useI18n();
const rootAttrs = useAttrs();
</script>
