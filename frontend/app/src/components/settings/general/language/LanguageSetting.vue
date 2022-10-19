<template>
  <div class="d-flex align-center">
    <settings-option
      #default="{ error, success, update }"
      class="fill-width"
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
        :label="t('general_settings.labels.language')"
        persistent-hint
        :success-messages="success"
        :error-messages="error"
        v-bind="rootAttrs"
        @change="update"
      >
        <template #item="{ item }">
          <language-selector-item
            :countries="item.countries ?? [item.identifier]"
            :label="item.label"
          />
        </template>
        <template #selection="{ item }">
          <language-selector-item
            :countries="item.countries ?? [item.identifier]"
            :label="item.label"
          />
        </template>
      </v-select>
    </settings-option>
    <div class="ml-2">
      <v-tooltip open-delay="400" bottom max-width="400">
        <template #activator="{ on }">
          <base-external-link
            :href="contributeUrl + '#add-a-new-language-or-translation'"
          >
            <v-btn icon v-on="on">
              <v-icon>mdi-account-edit</v-icon>
            </v-btn>
          </base-external-link>
        </template>
        <span>
          {{ t('general_settings.language_contribution_tooltip') }}
        </span>
      </v-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, ref, useAttrs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import LanguageSelectorItem from '@/components/settings/general/language/LanguageSelectorItem.vue';
import { supportedLanguages } from '@/data/supported-language';
import { useInterop } from '@/electron-interop';
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

const { contributeUrl } = useInterop();
</script>
