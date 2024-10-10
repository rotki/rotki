<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import { ThemeManager } from '@/premium/premium';
import { usePremium } from '@/composables/premium';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_INTERFACE,
  },
});

const premium = usePremium();
const { t } = useI18n();

enum Category {
  GENERAL = 'general',
  GRAPH = 'graph',
  ALIAS = 'alias',
  THEME = 'theme',
}

const navigation = [
  { id: Category.GENERAL, label: t('frontend_settings.title') },
  { id: Category.GRAPH, label: t('frontend_settings.subtitle.graph_basis') },
  { id: Category.ALIAS, label: t('frontend_settings.subtitle.alias_names') },
  { id: Category.THEME, label: t('premium_components.theme_manager.text') },
];
</script>

<template>
  <SettingsPage :navigation="navigation">
    <SettingCategory :id="Category.GENERAL">
      <template #title>
        {{ t('frontend_settings.title') }}
      </template>
      <LanguageSetting />
      <AnimationsEnabledSetting />
      <ScrambleDataSetting />
      <TimeFrameSetting />
      <RefreshSetting />
      <QueryPeriodSetting />
      <Explorers />
    </SettingCategory>

    <SettingCategory :id="Category.GRAPH">
      <template #title>
        {{ t('frontend_settings.subtitle.show_graph_range_selector') }}
      </template>
      <ZeroBasedGraphSetting />
      <ShowGraphRangeSelectorSetting />
    </SettingCategory>

    <SettingCategory :id="Category.ALIAS">
      <template #title>
        {{ t('frontend_settings.subtitle.alias_names') }}
      </template>
      <EnableEnsNamesSetting />
      <AddressNamePrioritySetting />
    </SettingCategory>

    <SettingCategory :id="Category.THEME">
      <template #title>
        {{ t('frontend_settings.subtitle.theme') }}
      </template>
      <ThemeManager
        v-if="premium"
        class="mt-12"
      />
      <ThemeManagerLock
        v-else
        class="mt-12"
      />
    </SettingCategory>
  </SettingsPage>
</template>
