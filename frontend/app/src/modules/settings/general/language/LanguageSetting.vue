<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { supportedLanguages } from '@/modules/core/common/supported-language';
import { useLocale } from '@/modules/session/use-locale';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import LanguageSelectorItem from '@/modules/settings/general/language/LanguageSelectorItem.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { SupportedLanguage } from '@/modules/settings/types/frontend-settings';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

defineOptions({
  inheritAttrs: false,
});

const { useLocalSetting = false } = defineProps<{
  dense?: boolean;
  showLabel?: boolean;
  useLocalSetting?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const language = ref<SupportedLanguage>(SupportedLanguage.EN);

const { adaptiveLanguage, forceUpdateMachineLanguage, lastLanguage } = useLocale();
const { error: writeError, flush, model, success: writeSuccess } = useSettingModel('language');
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

async function updateSetting(value: SupportedLanguage): Promise<void> {
  clearAll();
  if (useLocalSetting) {
    set(lastLanguage, value);
  }
  else {
    set(model, value);
    await flush();
  }
}

function updateForceUpdateMachineLanguage(event: boolean | null): void {
  set(forceUpdateMachineLanguage, event ? 'true' : 'false');
}

watch(model, () => {
  clearAll();
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess('', true);
});

watch(writeError, (message) => {
  if (message)
    setError(`${t('general_settings.language.validation.error')}: ${message}`, true);
});

onMounted(() => {
  set(language, get(adaptiveLanguage));
});
</script>

<template>
  <SettingsItem
    :id="SettingsHighlightIds.LANGUAGE"
    class="w-full"
  >
    <template #title>
      {{ t('general_settings.language.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.language.subtitle') }}
    </template>
    <RuiMenuSelect
      v-model="language"
      :options="supportedLanguages"
      :label="t('general_settings.language.label')"
      :success-messages="success"
      :error-messages="error"
      hide-details
      key-attr="identifier"
      variant="outlined"
      v-bind="$attrs"
      @update:model-value="updateSetting($event as SupportedLanguage)"
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
      color="primary"
      class="mt-2"
      :model-value="forceUpdateMachineLanguage === 'true'"
      @update:model-value="updateForceUpdateMachineLanguage($event)"
    >
      {{ t('general_settings.language.force_saved_language_setting_in_machine_hint') }}
    </RuiCheckbox>

    <RuiAlert
      type="warning"
      class="mt-4"
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
  </SettingsItem>
</template>
