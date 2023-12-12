<script setup lang="ts">
import { supportedLanguages } from '@/data/supported-language';
import { SupportedLanguage } from '@/types/settings/frontend-settings';

const props = withDefaults(
  defineProps<{
    dense?: boolean;
    showLabel?: boolean;
    useLocalSetting?: boolean;
  }>(),
  {
    dense: false,
    showLabel: true,
    useLocalSetting: false
  }
);

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

<template>
  <div>
    <div class="flex items-center gap-2">
      <SettingsOption
        #default="{ error, success, update }"
        class="w-full"
        setting="language"
        frontend-setting
        :error-message="t('general_settings.validation.language.error')"
      >
        <VSelect
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
            <LanguageSelectorItem
              :countries="item.countries ?? [item.identifier]"
              :label="item.label"
            />
          </template>
          <template #selection="{ item }">
            <LanguageSelectorItem
              :countries="item.countries ?? [item.identifier]"
              :label="item.label"
            />
          </template>
        </VSelect>
      </SettingsOption>
      <RuiTooltip
        :popper="{ placement: 'bottom', offsetDistance: 0 }"
        tooltip-class="max-w-[25rem]"
      >
        <template #activator>
          <ExternalLink :url="languageContributeUrl" custom>
            <RuiButton variant="text" icon>
              <RuiIcon name="file-edit-line" />
            </RuiButton>
          </ExternalLink>
        </template>
        <span>
          {{ t('general_settings.language_contribution_tooltip') }}
        </span>
      </RuiTooltip>
    </div>
    <RuiCheckbox
      v-if="!useLocalSetting"
      hide-details
      class="mt-1"
      color="primary"
      :value="forceUpdateMachineLanguage === 'true'"
      @input="updateForceUpdateMachineLanguage($event)"
    >
      {{
        t(
          'general_settings.labels.force_saved_language_setting_in_machine_hint'
        )
      }}
    </RuiCheckbox>
  </div>
</template>
