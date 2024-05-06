<script setup lang="ts">
import { supportedLanguages } from '@/data/supported-language';
import { SupportedLanguage } from '@/types/settings/frontend-settings';
import { externalLinks } from '@/data/external-links';

const props = withDefaults(
  defineProps<{
    dense?: boolean;
    showLabel?: boolean;
    useLocalSetting?: boolean;
  }>(),
  {
    dense: false,
    showLabel: true,
    useLocalSetting: false,
  },
);

const { useLocalSetting } = toRefs(props);

const language = ref<string>(SupportedLanguage.EN);

const { lastLanguage } = useLastLanguage();

async function updateSetting(value: string, update: (newValue: any) => Promise<void>) {
  if (get(useLocalSetting))
    set(lastLanguage, value);
  else
    await update(value);
}

const { forceUpdateMachineLanguage } = useLastLanguage();
const { adaptiveLanguage } = storeToRefs(useSessionStore());

function updateForceUpdateMachineLanguage(event: boolean | null) {
  set(forceUpdateMachineLanguage, event ? 'true' : 'false');
}

onMounted(() => {
  set(language, get(adaptiveLanguage));
});

const { t } = useI18n();
const rootAttrs = useAttrs();
</script>

<template>
  <div>
    <div class="flex items-center gap-2">
      <SettingsOption
        #default="{ error, success, updateImmediate }"
        class="w-full"
        setting="language"
        frontend-setting
        :error-message="t('general_settings.validation.language.error')"
      >
        <RuiMenuSelect
          v-model="language"
          :options="supportedLanguages"
          :label="t('general_settings.labels.language')"
          :success-messages="success"
          :error-messages="error"
          :show-details="!!success || !!error"
          key-attr="identifier"
          text-attr="label"
          full-width
          variant="outlined"
          v-bind="rootAttrs"
          @input="updateSetting($event, updateImmediate)"
        >
          <template #activator.text="{ value }">
            <LanguageSelectorItem
              :countries="value.countries ?? [value.identifier]"
              :label="value.label"
            />
          </template>
          <template #item.text="{ option }">
            <LanguageSelectorItem
              :countries="option.countries ?? [option.identifier]"
              :label="option.label"
            />
          </template>
        </RuiMenuSelect>
      </SettingsOption>
      <RuiTooltip
        :popper="{ placement: 'bottom', offsetDistance: 0 }"
        tooltip-class="max-w-[25rem]"
      >
        <template #activator>
          <ExternalLink
            :url="externalLinks.contributeSection.language"
            custom
          >
            <RuiButton
              variant="text"
              icon
            >
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
          'general_settings.labels.force_saved_language_setting_in_machine_hint',
        )
      }}
    </RuiCheckbox>
  </div>
</template>
