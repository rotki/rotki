<script setup lang="ts">
import { msg } from '@/message-key';
import NewlyDetectedTokensSettingsCategory from '@/modules/assets/detection/settings/NewlyDetectedTokensSettingsCategory.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import AliasSettingsCategory from '@/modules/settings/frontend/AliasSettingsCategory.vue';
import GraphSettingsCategory from '@/modules/settings/frontend/GraphSettingsCategory.vue';
import InterfaceOnlyCategory from '@/modules/settings/frontend/InterfaceOnlyCategory.vue';
import PrivacySettingsCategory from '@/modules/settings/frontend/PrivacySettingsCategory.vue';
import RefreshSettingsCategory from '@/modules/settings/frontend/RefreshSettingsCategory.vue';
import ThemeSettingsCategory from '@/modules/settings/frontend/ThemeSettingsCategory.vue';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.settings_sub.interface'), icon: 'lu-laptop-minimal', parent: '/settings' },
    noteLocation: NoteLocation.SETTINGS_INTERFACE,
  },
});

const { t } = useI18n({ useScope: 'global' });

const navigation = computed<{ id: string; label: string }[]>(() => [
  { id: SettingsCategoryIds.INTERFACE_ONLY, label: t('frontend_settings.sections.display') },
  { id: SettingsCategoryIds.PRIVACY, label: t('frontend_settings.sections.privacy') },
  { id: SettingsCategoryIds.REFRESH, label: t('frontend_settings.sections.refresh') },
  { id: SettingsCategoryIds.GRAPH, label: t('frontend_settings.sections.graphs') },
  { id: SettingsCategoryIds.ALIAS, label: t('frontend_settings.sections.addresses') },
  { id: SettingsCategoryIds.NEWLY_DETECTED_TOKENS, label: t('frontend_settings.newly_detected_tokens.title') },
  { id: SettingsCategoryIds.THEME, label: t('premium_components.theme_manager.text') },
]);
</script>

<template>
  <SettingsPage :navigation="navigation">
    <InterfaceOnlyCategory :id="SettingsCategoryIds.INTERFACE_ONLY" />
    <PrivacySettingsCategory :id="SettingsCategoryIds.PRIVACY" />
    <RefreshSettingsCategory :id="SettingsCategoryIds.REFRESH" />
    <GraphSettingsCategory :id="SettingsCategoryIds.GRAPH" />
    <AliasSettingsCategory :id="SettingsCategoryIds.ALIAS" />
    <NewlyDetectedTokensSettingsCategory :id="SettingsCategoryIds.NEWLY_DETECTED_TOKENS" />
    <ThemeSettingsCategory :id="SettingsCategoryIds.THEME" />
  </SettingsPage>
</template>
