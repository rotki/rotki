<script setup lang="ts">
import Explorers from '@/components/settings/explorers/Explorers.vue';
import AnimationsEnabledSetting from '@/components/settings/frontend/AnimationsEnabledSetting.vue';
import PersistTableSortingSetting from '@/components/settings/frontend/PersistTableSortingSetting.vue';
import ScrambleDataSetting from '@/components/settings/frontend/ScrambleDataSetting.vue';
import LanguageSetting from '@/components/settings/general/language/LanguageSetting.vue';
import QueryPeriodSetting from '@/components/settings/general/QueryPeriodSetting.vue';
import RefreshSetting from '@/components/settings/general/RefreshSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';

const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.title') }}
    </template>
    <LanguageSetting />
    <AnimationsEnabledSetting />
    <PersistTableSortingSetting />
    <ScrambleDataSetting />
    <RefreshSetting />
    <QueryPeriodSetting />
    <Explorers />
  </SettingCategory>
</template>
