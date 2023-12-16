<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library';

const { isMini, showDrawer } = storeToRefs(useAreaVisibilityStore());
const { appVersion } = storeToRefs(useMainStore());

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
        <RotkiLogo
          :text="!isMini"
          :size="isMini ? 1.625 : 3"
        />
      </div>
      <NavigationMenu :is-mini="isMini" />
    </div>
    <div
      v-if="!isMini"
      class="p-2 text-center border-t border-default text-overline"
    >
      {{ appVersion }}
    </div>
  </RuiNavigationDrawer>
</template>
