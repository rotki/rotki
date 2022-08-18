<template>
  <div>
    <no-premium-placeholder
      v-if="!premium"
      :text="tc('liquity_page.no_premium')"
    />
    <module-not-active v-else-if="!moduleEnabled" :modules="modules" />
    <progress-screen v-else-if="loading">
      <template #message>
        {{ tc('liquity_page.loading') }}
      </template>
    </progress-screen>
    <div v-else>
      <liquity-staking-details>
        <template #modules>
          <active-modules :modules="modules" />
        </template>
      </liquity-staking-details>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, watch } from '@vue/composition-api';
import { useI18n } from 'vue-i18n-composable';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import LiquityStakingDetails from '@/components/staking/liquity/LiquityStakingDetails.vue';
import { setupStatusChecking } from '@/composables/common';
import { getPremium, useModules } from '@/composables/session';
import { Section } from '@/store/const';
import { useLiquityStore } from '@/store/defi/liquity';
import { Module } from '@/types/modules';

export default defineComponent({
  name: 'LiquityPage',
  components: {
    LiquityStakingDetails,
    NoPremiumPlaceholder,
    ProgressScreen,
    ActiveModules,
    ModuleNotActive
  },
  setup() {
    const { isModuleEnabled } = useModules();
    const { fetchStaking, fetchStakingEvents } = useLiquityStore();

    async function load() {
      await fetchStaking();
      await fetchStakingEvents();
    }

    onMounted(async () => await load());
    const { shouldShowLoadingScreen } = setupStatusChecking();
    const modules = [Module.LIQUITY];
    const moduleEnabled = isModuleEnabled(modules[0]);

    watch(moduleEnabled, async enabled => {
      if (enabled) {
        await load();
      }
    });

    const { tc } = useI18n();
    return {
      moduleEnabled: moduleEnabled,
      modules,
      loading: shouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING),
      premium: getPremium(),
      tc
    };
  }
});
</script>
