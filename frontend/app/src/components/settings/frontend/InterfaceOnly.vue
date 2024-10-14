<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.title') }}
    </template>
    <SettingsItem>
      <template #title>
        {{ t('general_settings.labels.language_title') }}
      </template>
      <template #subtitle>
        {{ t('general_settings.labels.language_subtitle') }}
      </template>
      <LanguageSetting />
    </SettingsItem>
    <SettingsItem>
      <template #title>
        {{ t('frontend_settings.label.animations') }}
      </template>
      <AnimationsEnabledSetting />
    </SettingsItem>
    <SettingsItem>
      <template #title>
        {{ t('frontend_settings.label.scramble') }}
      </template>
      <ScrambleDataSetting />
    </SettingsItem>
    <SettingsItem>
      <template #title>
        {{ t('frontend_settings.subtitle.refresh') }}
      </template>
      <RefreshSetting />
    </SettingsItem>
    <SettingsItem>
      <template #title>
        {{ t('frontend_settings.subtitle.query') }}
      </template>
      <QueryPeriodSetting />
    </SettingsItem>
    <SettingsItem>
      <template #title>
        {{ t('explorers.title') }}
      </template>
      <template #subtitle>
        {{ t('explorers.subtitle') }}
      </template>
      <Explorers />
    </SettingsItem>
  </SettingCategory>
</template>
