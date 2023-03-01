<script setup lang="ts">
import { Sushi } from '@/premium/premium';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const section = Section.DEFI_SUSHISWAP_BALANCES;
const secondSection = Section.DEFI_SUSHISWAP_EVENTS;
const modules: Module[] = [Module.SUSHISWAP];

const { fetchBalances, fetchEvents } = useSushiswapStore();
const { isModuleEnabled } = useModules();
const { shouldShowLoadingScreen, isLoading } = useStatusStore();
const premium = usePremium();
const { tc } = useI18n();

const primaryRefreshing = isLoading(section);
const secondaryRefreshing = isLoading(secondSection);
const loading = shouldShowLoadingScreen(section);
const isEnabled = isModuleEnabled(modules[0]);

onMounted(async () => {
  await Promise.all([fetchBalances(false), fetchEvents(false)]);
});
</script>

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
