<script setup lang="ts">
import { Sushi } from '@/premium/premium';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useStatusStore } from '@/store/status';
import { useModules } from '@/composables/session/modules';
import { usePremium } from '@/composables/premium';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';

const section = Section.DEFI_SUSHISWAP_BALANCES;
const secondSection = Section.DEFI_SUSHISWAP_EVENTS;
const modules: Module[] = [Module.SUSHISWAP];

const { fetchBalances, fetchEvents } = useSushiswapStore();
const { isModuleEnabled } = useModules();
const { isLoading, shouldShowLoadingScreen } = useStatusStore();
const premium = usePremium();
const { t } = useI18n();

const primaryRefreshing = isLoading(section);
const secondaryRefreshing = isLoading(secondSection);
const loading = shouldShowLoadingScreen(section);
const isEnabled = isModuleEnabled(modules[0]);

async function refresh(ignoreCache: boolean = false) {
  await Promise.all([fetchBalances(ignoreCache), fetchEvents(ignoreCache)]);
}

onMounted(async () => {
  await refresh();
});

const refreshTooltip = computed<string>(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.sushiswap').toLocaleLowerCase(),
  }),
);
</script>

<template>
  <NoPremiumPlaceholder
    v-if="!premium"
    :text="t('sushiswap.premium')"
  />
  <ModuleNotActive
    v-else-if="!isEnabled"
    :modules="modules"
  />
  <ProgressScreen v-else-if="loading">
    <template #message>
      {{ t('sushiswap.loading') }}
    </template>
  </ProgressScreen>
  <TablePageLayout
    v-else
    child
    :title="[
      t('navigation_menu.defi'),
      t('navigation_menu.defi_sub.deposits_sub.liquidity'),
      t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.sushiswap'),
    ]"
  >
    <template #buttons>
      <div class="flex items-center gap-4">
        <ActiveModules :modules="modules" />

        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              variant="outlined"
              color="primary"
              :loading="primaryRefreshing || secondaryRefreshing"
              @click="refresh(true)"
            >
              <template #prepend>
                <RuiIcon name="lu-refresh-ccw" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ refreshTooltip }}
        </RuiTooltip>
      </div>
    </template>

    <Sushi
      :refreshing="primaryRefreshing || secondaryRefreshing"
      :secondary-loading="secondaryRefreshing"
    />
  </TablePageLayout>
</template>
