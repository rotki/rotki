<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import LanguageSelectorItem from '@/components/settings/general/language/LanguageSelectorItem.vue';
import { useLocale } from '@/composables/session/use-locale';
import { supportedLanguages } from '@/data/supported-language';
import { SupportedLanguage } from '@/types/settings/frontend-settings';
import { externalLinks } from '@shared/external-links';

defineOptions({
  inheritAttrs: false,
});

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

const language = ref<SupportedLanguage>(SupportedLanguage.EN);

const { adaptiveLanguage, forceUpdateMachineLanguage, lastLanguage } = useLocale();

async function updateSetting(value: string, update: (newValue: any) => Promise<void>) {
  if (get(useLocalSetting))
    set(lastLanguage, value);
  else
    await update(value);
}

function updateForceUpdateMachineLanguage(event: boolean | null) {
  set(forceUpdateMachineLanguage, event ? 'true' : 'false');
}

onMounted(() => {
  set(language, get(adaptiveLanguage));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    class="w-full"
    setting="language"
    frontend-setting
    :error-message="t('general_settings.language.validation.error')"
  >
    <template #title>
      {{ t('general_settings.language.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.language.subtitle') }}
    </template>
    <template #default="{ error, success, updateImmediate }">
      <RuiAlert
        type="warning"
        class="mb-6"
      >
        {{ t('general_settings.language.contribution') }}
        <ExternalLink
          :url="externalLinks.contributeSection.language"
          custom
        >
          <RuiButton
            variant="text"
            color="primary"
            size="sm"
            class="-ml-1.5 mt-3"
          >
            {{ t('general_settings.language.click_here') }}
            <template #append>
              <RuiIcon
                name="lu-external-link"
                size="16"
              />
            </template>
          </RuiButton>
        </ExternalLink>
      </RuiAlert>
      <RuiMenuSelect
        v-model="language"
        :options="supportedLanguages"
        :label="t('general_settings.language.label')"
        :success-messages="success"
        :error-messages="error"
        key-attr="identifier"
        variant="outlined"
        v-bind="$attrs"
        @update:model-value="updateSetting($event as SupportedLanguage, updateImmediate)"
      >
        <template #selection="{ item }">
          <LanguageSelectorItem
            :countries="item.countries ?? [item.identifier]"
            :label="item.label"
          />
        </template>
        <template #item="{ item }">
          <LanguageSelectorItem
            :countries="item.countries ?? [item.identifier]"
            :label="item.label"
          />
        </template>
      </RuiMenuSelect>

      <RuiCheckbox
        v-if="!useLocalSetting"
        hide-details
        class="mt-1"
        color="primary"
        :model-value="forceUpdateMachineLanguage === 'true'"
        @update:model-value="updateForceUpdateMachineLanguage($event)"
      >
        {{ t('general_settings.language.force_saved_language_setting_in_machine_hint') }}
      </RuiCheckbox>
    </template>
  </SettingsOption>
</template>
