<template>
  <div>
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
          @change="updateSetting($event, update)"
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
            <base-external-link :href="languageContributeUrl">
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
    <div v-if="!useLocalSetting" class="mb-n10">
      <v-row>
        <v-col cols="auto">
          <v-checkbox
            :input-value="forceUpdateMachineLanguage === 'true'"
            :label="
              t(
                'general_settings.labels.force_saved_language_setting_in_machine_hint'
              )
            "
            @change="updateForceUpdateMachineLanguage($event)"
          />
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import LanguageSelectorItem from '@/components/settings/general/language/LanguageSelectorItem.vue';
import { useLastLanguage } from '@/composables/session/language';
import { supportedLanguages } from '@/data/supported-language';
import { useInterop } from '@/electron-interop';
import { useSessionStore } from '@/store/session';
import { SupportedLanguage } from '@/types/frontend-settings';

const props = defineProps({
  dense: {
    required: false,
    type: Boolean,
    default: false
  },
  showLabel: {
    required: false,
    type: Boolean,
    default: true
  },
  useLocalSetting: {
    required: false,
    type: Boolean,
    default: false
  }
});

const { useLocalSetting } = toRefs(props);

const language = ref<string>(SupportedLanguage.EN);

const { lastLanguage } = useLastLanguage();

const updateSetting = async (
  value: string,
  update: (newValue: any) => Promise<void>
) => {
  if (get(useLocalSetting)) {
    set(lastLanguage, value);
  } else {
    await update(value);
  }
};

const { forceUpdateMachineLanguage } = useLastLanguage();
const { adaptiveLanguage } = storeToRefs(useSessionStore());

const updateForceUpdateMachineLanguage = (event: boolean | null) => {
  set(forceUpdateMachineLanguage, event ? 'true' : 'false');
};

onMounted(() => {
  set(language, get(adaptiveLanguage));
});

const { t } = useI18n();
const rootAttrs = useAttrs();

const { languageContributeUrl } = useInterop();
</script>
