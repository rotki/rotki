<script setup lang="ts">
import { BalancerBalances } from '@/premium/premium';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const modules: Module[] = [Module.BALANCER];

const { fetchBalances, fetchEvents } = useBalancerStore();
const { isModuleEnabled } = useModules();
const { shouldShowLoadingScreen, isLoading } = useStatusStore();

const premium = usePremium();
const isEnabled = computed(() => isModuleEnabled(modules[0]));
const balancesLoading = shouldShowLoadingScreen(Section.DEFI_BALANCER_BALANCES);
const eventsLoading = shouldShowLoadingScreen(Section.DEFI_BALANCER_EVENTS);
const loading = computed(() => get(balancesLoading) && get(eventsLoading));
const balancesRefreshing = isLoading(Section.DEFI_BALANCER_BALANCES);
const eventsRefreshing = isLoading(Section.DEFI_BALANCER_EVENTS);
const refreshing = computed(
  () => get(balancesRefreshing) || get(eventsRefreshing)
);

const { t } = useI18n();

const refresh = async (ignoreCache: boolean = false) => {
  await Promise.all([fetchBalances(ignoreCache), fetchEvents(ignoreCache)]);
};

onMounted(async () => {
  await refresh();
});

const refreshTooltip: ComputedRef<string> = computed(() =>
  t('helpers.refresh_header.tooltip', {
    title: t(
      'navigation_menu.defi_sub.deposits_sub.liquidity_sub.balancer'
    ).toLocaleLowerCase()
  })
);
</script>

<template>
  <NoPremiumPlaceholder v-if="!premium" :text="t('balancer.premium')" />
  <ModuleNotActive v-else-if="!isEnabled" :modules="modules" />
  <ProgressScreen v-else-if="loading">
    <template #message>
      {{ t('balancer.loading') }}
    </template>
  </ProgressScreen>
  <TablePageLayout
    v-else
    class="mt-8"
    :title="[
      t('navigation_menu.defi'),
      t('navigation_menu.defi_sub.deposits_sub.liquidity'),
      t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.balancer')
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
              :loading="refreshing"
              @click="refresh(true)"
            >
              <template #prepend>
                <RuiIcon name="refresh-line" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ refreshTooltip }}
        </RuiTooltip>
      </div>
    </template>

    <BalancerBalances />
  </TablePageLayout>
</template>
