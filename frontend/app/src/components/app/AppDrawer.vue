<script setup lang="ts">
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import GlobalSearch from '@/components/GlobalSearch.vue';
import NavigationMenu from '@/components/NavigationMenu.vue';
import { Routes } from '@/router/routes';
import { useMainStore } from '@/store/main';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const demoMode = import.meta.env.VITE_DEMO_MODE;
const { isMini, showDrawer } = storeToRefs(useAreaVisibilityStore());
const { appVersion } = storeToRefs(useMainStore());
const { isXlAndDown } = useBreakpoint();
const route = useRoute();

const version = computed<string>(() => {
  const version = get(appVersion);
  if (demoMode === undefined) {
    return version;
  }

  const sanitizedVersion = version.replace('.dev', '');
  const splitVersion = sanitizedVersion.split('.');
  if (demoMode === 'minor') {
    splitVersion[1] = `${parseInt(splitVersion[1]) + 1}`;
    splitVersion[2] = '0';
  }
  else if (demoMode === 'patch') {
    splitVersion[2] = `${parseInt(splitVersion[2]) + 1}`;
  }
  return splitVersion.join('.');
});

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
      <GlobalSearch />
      <NavigationMenu :is-mini="isMini" />
    </div>
    <div
      v-if="!isMini"
      class="p-2 text-center border-t border-default text-overline"
    >
      {{ version }}
    </div>
  </RuiNavigationDrawer>
</template>
