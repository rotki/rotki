<script setup lang="ts">
import { supportedLanguages } from '@/data/supported-language';
import { SupportedLanguage } from '@/types/settings/frontend-settings';

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

const { lastLanguage } = useLastLanguage();

async function updateSetting(value: string, update: (newValue: any) => Promise<void>) {
  if (get(useLocalSetting))
    set(lastLanguage, value);
  else await update(value);
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
</script>

<template>
  <div>
    <div class="flex gap-2">
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
              class="mt-1"
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
      :model-value="forceUpdateMachineLanguage === 'true'"
      @update:model-value="updateForceUpdateMachineLanguage($event)"
    >
      {{ t('general_settings.labels.force_saved_language_setting_in_machine_hint') }}
    </RuiCheckbox>
  </div>
</template>
