<script setup lang="ts">
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import GlobalSearch from '@/components/GlobalSearch.vue';
import NavigationMenu from '@/components/NavigationMenu.vue';
import SponsorshipView from '@/components/sponsorship/SponsorshipView.vue';
import { Routes } from '@/router/routes';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const { isMini, showDrawer } = storeToRefs(useAreaVisibilityStore());
const { isXlAndDown } = useBreakpoint();
const route = useRoute();

watch(route, () => {
  if (get(showDrawer) && get(isXlAndDown))
    set(showDrawer, false);
});
</script>

<template>
  <RuiNavigationDrawer
    v-model="showDrawer"
    width="300"
    :content-class="{
      'flex flex-col border-r border-rui-grey-300 dark:border-rui-grey-800': true,
      '!top-0 !max-h-full': isXlAndDown,
    }"
    :mini-variant="!isXlAndDown"
    :overlay="isXlAndDown"
  >
    <div class="flex-1 overflow-y-auto overflow-x-hidden pb-2">
      <div
        class="flex py-6"
        :class="{
          'px-4': !isMini,
          'px-0 [&>div]:h-8 justify-center': isMini,
        }"
      >
        <RouterLink :to="Routes.DASHBOARD">
          <RotkiLogo
            :text="!isMini"
            :size="isMini ? 1.625 : 3"
          />
        </RouterLink>
      </div>
      <GlobalSearch :is-mini="isMini" />
      <NavigationMenu :is-mini="isMini" />
    </div>
    <div
      v-if="!isMini"
      class="px-6 py-3 border-t border-default"
    >
      <SponsorshipView drawer />
    </div>
  </RuiNavigationDrawer>
</template>
