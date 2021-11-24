<template>
  <div>
    <no-premium-placeholder
      v-if="!premium"
      :text="$t('liquity_page.no_premium')"
    />
    <module-not-active v-else-if="!moduleEnabled" :modules="modules" />
    <progress-screen v-else-if="loading">
      <template #message>
        {{ $t('liquity_page.loading') }}
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
import { defineComponent, onMounted } from '@vue/composition-api';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import LiquityStakingDetails from '@/components/staking/liquity/LiquityStakingDetails.vue';
import { setupStatusChecking } from '@/composables/common';
import { getPremium, setupModuleEnabled } from '@/composables/session';
import { Section } from '@/store/const';
import { useStore } from '@/store/utils';
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
    const { isModuleEnabled } = setupModuleEnabled();
    const store = useStore();
    onMounted(async () => {
      await store.dispatch('defi/liquity/fetchStaking');
      await store.dispatch('defi/liquity/fetchStakingEvents');
    });
    const modules = [Module.LIQUITY];
    const { shouldShowLoadingScreen } = setupStatusChecking();
    return {
      moduleEnabled: isModuleEnabled(modules[0]),
      modules,
      loading: shouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING),
      premium: getPremium()
    };
  }
});
</script>
