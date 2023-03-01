<script setup lang="ts">
import { ThemeManager } from '@/premium/premium';

const { premium } = storeToRefs(usePremiumStore());

const { t } = useI18n();
</script>

<template>
  <setting-category>
    <template #title>
      {{ t('frontend_settings.title') }}
    </template>

    <animations-enabled-setting />
    <scramble-data-setting />

    <div class="mt-8">
      <div class="d-flex align-center">
        <div class="text-h6">
          {{ t('frontend_settings.subtitle.alias_names') }}
        </div>
      </div>
      <enable-ens-names-setting />
      <address-name-priority-setting />
    </div>

    <time-frame-setting />

    <div class="mt-8">
      <div class="text-h6">
        {{ t('frontend_settings.subtitle.graph_basis') }}
      </div>
      <zero-based-graph-setting />
    </div>

    <div class="mt-8">
      <div class="text-h6">
        {{ t('frontend_settings.subtitle.show_graph_range_selector') }}
      </div>
      <show-graph-range-selector-setting />
    </div>

    <div class="mt-4">
      <div class="text-h6">
        {{ t('frontend_settings.subtitle.include_nfts') }}
      </div>
      <nfts-in-net-value-setting />
    </div>

    <refresh-setting />
    <query-period-setting />
    <explorers />
    <theme-manager v-if="premium" class="mt-12" />
    <theme-manager-lock v-else class="mt-12" />
  </setting-category>
</template>
