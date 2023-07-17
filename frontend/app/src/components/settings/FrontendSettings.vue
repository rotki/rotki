<script setup lang="ts">
import { ThemeManager } from '@/premium/premium';

const { premium } = storeToRefs(usePremiumStore());

const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.title') }}
    </template>

    <AnimationsEnabledSetting />
    <ScrambleDataSetting />

    <div class="mt-8">
      <div class="d-flex align-center">
        <div class="text-h6">
          {{ t('frontend_settings.subtitle.alias_names') }}
        </div>
      </div>
      <EnableEnsNamesSetting />
      <AddressNamePrioritySetting />
    </div>

    <TimeFrameSetting />

    <div class="mt-8">
      <div class="text-h6">
        {{ t('frontend_settings.subtitle.graph_basis') }}
      </div>
      <ZeroBasedGraphSetting />
    </div>

    <div class="mt-8">
      <div class="text-h6">
        {{ t('frontend_settings.subtitle.show_graph_range_selector') }}
      </div>
      <ShowGraphRangeSelectorSetting />
    </div>

    <RefreshSetting />
    <QueryPeriodSetting />
    <Explorers />
    <ThemeManager v-if="premium" class="mt-12" />
    <ThemeManagerLock v-else class="mt-12" />
  </SettingCategory>
</template>
