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
const { t } = useI18n();

const primaryRefreshing = isLoading(section);
const secondaryRefreshing = isLoading(secondSection);
const loading = shouldShowLoadingScreen(section);
const isEnabled = isModuleEnabled(modules[0]);

onMounted(async () => {
  await Promise.all([fetchBalances(false), fetchEvents(false)]);
});
</script>

<template>
  <NoPremiumPlaceholder v-if="!premium" :text="t('sushiswap.premium')" />
  <ModuleNotActive v-else-if="!isEnabled" :modules="modules" />
  <ProgressScreen v-else-if="loading">
    <template #message>
      {{ t('sushiswap.loading') }}
    </template>
  </ProgressScreen>
  <div v-else>
    <Sushi
      class="mt-4"
      :refreshing="primaryRefreshing || secondaryRefreshing"
      :secondary-loading="secondaryRefreshing"
    >
      <template #modules>
        <ActiveModules :modules="modules" />
      </template>
    </Sushi>
  </div>
</template>
