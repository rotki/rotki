<template>
  <module-not-active v-if="!enabled" :modules="module" />
  <progress-screen v-else-if="loading">
    <template #message>
      {{ t('adex_page.loading') }}
    </template>
  </progress-screen>
  <div v-else>
    <adex-staking
      :history-refreshing="secondaryRefreshing"
      :refreshing="primaryRefreshing || secondaryRefreshing"
    >
      <template #modules>
        <active-modules :modules="module" />
      </template>
    </adex-staking>
  </div>
</template>

<script setup lang="ts">
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { useSectionLoading } from '@/composables/common';
import { useModules } from '@/composables/session/modules';
import { AdexStaking } from '@/premium/premium';
import { useAdexStakingStore } from '@/store/staking';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const { isModuleEnabled } = useModules();
const enabled = isModuleEnabled(Module.ADEX);

const { fetchAdex } = useAdexStakingStore();
onBeforeMount(async () => {
  if (!get(enabled)) {
    return;
  }
  await fetchAdex(false);
});

const { isSectionRefreshing, shouldShowLoadingScreen } = useSectionLoading();

const loading = shouldShowLoadingScreen(Section.STAKING_ADEX);
const primaryRefreshing = isSectionRefreshing(Section.STAKING_ADEX);
const secondaryRefreshing = isSectionRefreshing(Section.STAKING_ADEX_HISTORY);

const module = [Module.ADEX];

const { t } = useI18n();
</script>

<style module lang="scss">
.modules {
  display: inline-flex;
  position: absolute;
  right: 65px;
  top: 58px;
}
</style>
