<script setup lang="ts">
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import AliasSettingsCategory from '@/components/settings/frontend/AliasSettingsCategory.vue';
import GraphSettingsCategory from '@/components/settings/frontend/GraphSettingsCategory.vue';
import InterfaceOnlyCategory from '@/components/settings/frontend/InterfaceOnlyCategory.vue';
import ThemeSettingsCategory from '@/components/settings/frontend/ThemeSettingsCategory.vue';
import { SettingsCategoryIds } from '@/composables/settings/types';
import { NoteLocation } from '@/modules/common/notes';
import NewlyDetectedTokensSettingsCategory from '@/modules/newly-detected-tokens/settings/NewlyDetectedTokensSettingsCategory.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_INTERFACE,
  },
});

const { t } = useI18n({ useScope: 'global' });

const navigation = computed<{ id: string; label: string }[]>(() => [
  { id: SettingsCategoryIds.INTERFACE_ONLY, label: t('frontend_settings.title') },
  { id: SettingsCategoryIds.GRAPH, label: t('frontend_settings.subtitle.graph_settings') },
  { id: SettingsCategoryIds.ALIAS, label: t('frontend_settings.subtitle.alias_names') },
  { id: SettingsCategoryIds.NEWLY_DETECTED_TOKENS, label: t('frontend_settings.newly_detected_tokens.title') },
  { id: SettingsCategoryIds.THEME, label: t('premium_components.theme_manager.text') },
]);
</script>

<template>
  <SettingsPage :navigation="navigation">
    <InterfaceOnlyCategory :id="SettingsCategoryIds.INTERFACE_ONLY" />
    <GraphSettingsCategory :id="SettingsCategoryIds.GRAPH" />
    <AliasSettingsCategory :id="SettingsCategoryIds.ALIAS" />
    <NewlyDetectedTokensSettingsCategory :id="SettingsCategoryIds.NEWLY_DETECTED_TOKENS" />
    <ThemeSettingsCategory :id="SettingsCategoryIds.THEME" />
  </SettingsPage>
</template>
