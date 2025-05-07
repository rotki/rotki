<script setup lang="ts">
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import AliasSettingsCategory from '@/components/settings/frontend/AliasSettingsCategory.vue';
import GraphSettingsCategory from '@/components/settings/frontend/GraphSettingsCategory.vue';
import InterfaceOnlyCategory from '@/components/settings/frontend/InterfaceOnlyCategory.vue';
import ThemeSettingsCategory from '@/components/settings/frontend/ThemeSettingsCategory.vue';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_INTERFACE,
  },
});

const { t } = useI18n({ useScope: 'global' });

enum Category {
  INTERFACE_ONLY = 'interface_only',
  GRAPH = 'graph',
  ALIAS = 'alias',
  THEME = 'theme',
}

const navigation = [
  { id: Category.INTERFACE_ONLY, label: t('frontend_settings.title') },
  { id: Category.GRAPH, label: t('frontend_settings.subtitle.graph_settings') },
  { id: Category.ALIAS, label: t('frontend_settings.subtitle.alias_names') },
  { id: Category.THEME, label: t('premium_components.theme_manager.text') },
];
</script>

<template>
  <SettingsPage :navigation="navigation">
    <InterfaceOnlyCategory :id="Category.INTERFACE_ONLY" />
    <GraphSettingsCategory :id="Category.GRAPH" />
    <AliasSettingsCategory :id="Category.ALIAS" />
    <ThemeSettingsCategory :id="Category.THEME" />
  </SettingsPage>
</template>
