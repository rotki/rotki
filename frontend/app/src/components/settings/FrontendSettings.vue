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
          {{ t('frontend_settings.subtitle.eth_names') }}
        </div>
        <div class="pl-2">
          <eth-names-hint />
        </div>
      </div>
      <enable-ens-names-setting />
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

<script setup lang="ts">
import EthNamesHint from '@/components/EthNamesHint.vue';
import ThemeManagerLock from '@/components/premium/ThemeManagerLock.vue';
import Explorers from '@/components/settings/explorers/Explorers.vue';
import AnimationsEnabledSetting from '@/components/settings/frontend/AnimationsEnabledSetting.vue';
import EnableEnsNamesSetting from '@/components/settings/frontend/EnableEnsNamesSetting.vue';
import NftsInNetValueSetting from '@/components/settings/frontend/NftsInNetValueSetting.vue';
import ScrambleDataSetting from '@/components/settings/frontend/ScrambleDataSetting.vue';
import ShowGraphRangeSelectorSetting from '@/components/settings/frontend/ShowGraphRangeSelectorSetting.vue';
import TimeFrameSetting from '@/components/settings/frontend/TimeFrameSetting.vue';
import ZeroBasedGraphSetting from '@/components/settings/frontend/ZeroBasedGraphSetting.vue';
import QueryPeriodSetting from '@/components/settings/general/QueryPeriodSetting.vue';
import RefreshSetting from '@/components/settings/general/RefreshSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { ThemeManager } from '@/premium/premium';
import { usePremiumStore } from '@/store/session/premium';

const { premium } = storeToRefs(usePremiumStore());

const { t } = useI18n();
</script>
