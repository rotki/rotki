<template>
  <module-not-active v-if="!enabled" :modules="module" />
  <progress-screen v-else-if="loading">
    <template #message>
      {{ $t('adex_page.loading') }}
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

<script lang="ts">
import { defineComponent, onBeforeMount } from '@vue/composition-api';
import { get } from '@vueuse/core';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupStatusChecking } from '@/composables/common';
import { useModules } from '@/composables/session';
import { AdexStaking } from '@/premium/premium';
import { Section } from '@/store/const';
import { useAdexStakingStore } from '@/store/staking';
import { Module } from '@/types/modules';

export default defineComponent({
  name: 'AdexPage',
  components: { ActiveModules, ModuleNotActive, AdexStaking, ProgressScreen },
  setup() {
    const { isModuleEnabled } = useModules();
    const enabled = isModuleEnabled(Module.ADEX);

    const { fetchAdex } = useAdexStakingStore();
    onBeforeMount(async () => {
      if (!get(enabled)) {
        return;
      }
      await fetchAdex(false);
    });

    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const loading = shouldShowLoadingScreen(Section.STAKING_ADEX);
    const primaryRefreshing = isSectionRefreshing(Section.STAKING_ADEX);
    const secondaryRefreshing = isSectionRefreshing(
      Section.STAKING_ADEX_HISTORY
    );

    return {
      enabled,
      loading,
      primaryRefreshing,
      secondaryRefreshing,
      module: [Module.ADEX]
    };
  }
});
</script>

<style module lang="scss">
.modules {
  display: inline-flex;
  position: absolute;
  right: 65px;
  top: 58px;
}
</style>
