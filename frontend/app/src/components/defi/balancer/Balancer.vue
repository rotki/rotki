<template>
  <no-premium-placeholder v-if="!premium" :text="tc('balancer.premium')" />
  <module-not-active v-else-if="!isEnabled" :modules="modules" />
  <progress-screen v-else-if="loading">
    <template #message>
      {{ tc('balancer.loading') }}
    </template>
  </progress-screen>
  <div v-else>
    <balancer-balances class="mt-4" :refreshing="refreshing">
      <template #modules>
        <active-modules :modules="modules" />
      </template>
    </balancer-balances>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { useI18n } from 'vue-i18n-composable';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import { setupStatusChecking } from '@/composables/common';
import { getPremium, useModules } from '@/composables/session';
import { BalancerBalances } from '@/premium/premium';
import { Section } from '@/store/const';
import { useBalancerStore } from '@/store/defi/balancer';
import { Module } from '@/types/modules';

const modules: Module[] = [Module.BALANCER];

const { fetchBalances, fetchEvents } = useBalancerStore();
const { isModuleEnabled } = useModules();
const { shouldShowLoadingScreen, isSectionRefreshing } = setupStatusChecking();

const premium = getPremium();
const isEnabled = computed(() => isModuleEnabled(modules[0]));
const balancesLoading = shouldShowLoadingScreen(Section.DEFI_BALANCER_BALANCES);
const eventsLoading = shouldShowLoadingScreen(Section.DEFI_BALANCER_EVENTS);
const loading = computed(() => get(balancesLoading) && get(eventsLoading));
const balancesRefreshing = isSectionRefreshing(Section.DEFI_BALANCER_BALANCES);
const eventsRefreshing = isSectionRefreshing(Section.DEFI_BALANCER_EVENTS);
const refreshing = computed(
  () => get(balancesRefreshing) || get(eventsRefreshing)
);

const { tc } = useI18n();

onMounted(async () => {
  await Promise.allSettled([fetchBalances(false), fetchEvents(false)]);
});
</script>
