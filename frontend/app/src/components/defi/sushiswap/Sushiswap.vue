<template>
  <no-premium-placeholder v-if="!premium" :text="tc('sushiswap.premium')" />
  <module-not-active v-else-if="!isEnabled" :modules="modules" />
  <progress-screen v-else-if="loading">
    <template #message>
      {{ tc('sushiswap.loading') }}
    </template>
  </progress-screen>
  <div v-else>
    <sushi
      class="mt-4"
      :refreshing="primaryRefreshing || secondaryRefreshing"
      :secondary-loading="secondaryRefreshing"
    >
      <template #modules>
        <active-modules :modules="modules" />
      </template>
    </sushi>
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted } from '@vue/composition-api';
import { useI18n } from 'vue-i18n-composable';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import { setupStatusChecking } from '@/composables/common';
import { getPremium, useModules } from '@/composables/session';
import { Sushi } from '@/premium/premium';
import { Section } from '@/store/const';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { Module } from '@/types/modules';

export default defineComponent({
  name: 'Sushiswap',
  components: {
    ActiveModules,
    Sushi,
    NoPremiumPlaceholder,
    ProgressScreen,
    ModuleNotActive
  },
  setup() {
    const section = Section.DEFI_SUSHISWAP_BALANCES;
    const secondSection = Section.DEFI_SUSHISWAP_EVENTS;
    const modules: Module[] = [Module.SUSHISWAP];

    const { fetchBalances, fetchEvents } = useSushiswapStore();
    const { isModuleEnabled } = useModules();
    const { shouldShowLoadingScreen, isSectionRefreshing } =
      setupStatusChecking();
    const premium = getPremium();
    const { tc } = useI18n();

    onMounted(async () => {
      await Promise.all([fetchBalances(false), fetchEvents(false)]);
    });
    return {
      section,
      secondSection,
      modules,
      premium,
      primaryRefreshing: isSectionRefreshing(section),
      secondaryRefreshing: isSectionRefreshing(secondSection),
      loading: shouldShowLoadingScreen(section),
      isEnabled: isModuleEnabled(modules[0]),
      tc
    };
  }
});
</script>
