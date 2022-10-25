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

<script setup lang="ts">
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import LiquityStakingDetails from '@/components/staking/liquity/LiquityStakingDetails.vue';
import { useSectionLoading } from '@/composables/common';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { useLiquityStore } from '@/store/defi/liquity';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const modules = [Module.LIQUITY];
const { isModuleEnabled } = useModules();
const { fetchStaking, fetchStakingEvents } = useLiquityStore();
const { shouldShowLoadingScreen } = useSectionLoading();
const moduleEnabled = isModuleEnabled(modules[0]);
const loading = shouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING);
const premium = usePremium();

const load = async () => {
  await fetchStaking();
  await fetchStakingEvents();
};

onMounted(async () => await load());

watch(moduleEnabled, async enabled => {
  if (enabled) {
    await load();
  }
});

const { tc } = useI18n();
</script>
