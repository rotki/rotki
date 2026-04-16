<script setup lang="ts">
import AppDrawer from '@/components/app/AppDrawer.vue';
import AppIndicators from '@/components/app/AppIndicators.vue';
import AppSidebars from '@/components/app/AppSidebars.vue';
import NotificationPopup from '@/components/status/notifications/NotificationPopup.vue';
import { useInterop } from '@/composables/electron-interop';
import { initGraph } from '@/composables/init-graph';
import { useCoreScroll } from '@/composables/use-core-scroll';
import { useAreaVisibilityStore } from '@/modules/common/use-area-visibility-store';
import { useSessionAuthStore } from '@/modules/session/use-session-auth-store';
import SettingsSuggestionsDialog from '@/modules/settings/suggestions/SettingsSuggestionsDialog.vue';
import { useSettingsSuggestions } from '@/modules/settings/suggestions/use-settings-suggestions';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

const visibilityStore = useAreaVisibilityStore();
const { expanded, isMini, pinnedDragging, pinnedWidth, showPinned } = storeToRefs(visibilityStore);
const { overall } = storeToRefs(useStatisticsStore());
const { logged } = storeToRefs(useSessionAuthStore());
const { toggleDrawer } = visibilityStore;

const { updateTray } = useInterop();
const { scrollToTop, shouldShowScrollToTopButton } = useCoreScroll();

const { isXlAndDown } = useBreakpoint();
const { applySelected, dismissAll } = useSettingsSuggestions();
const frontendStore = useFrontendSettingsStore();

const pinnedPadding = computed<string | undefined>(() => {
  if (get(showPinned) && !get(isXlAndDown))
    return `calc(${get(pinnedWidth)}px - 100vw + 100%)`;

  return undefined;
});

watch(overall, (overall) => {
  if (overall.percentage === '-')
    return;

  updateTray(overall);
});

onBeforeMount(() => {
  initGraph();
});
</script>

<template>
  <div class="app__content">
    <NotificationPopup />
    <SettingsSuggestionsDialog
      v-model="frontendStore.showSuggestionsDialog"
      :suggestions="frontendStore.pendingSuggestions"
      @apply="applySelected($event)"
      @dismiss="dismissAll()"
    />
    <AppDrawer />

    <header
      class="app__app-bar fixed top-0 left-0 w-full bg-white dark:bg-dark-elevated md:h-16 h-[3.5rem] border-b border-rui-grey-300 dark:border-rui-grey-800"
    >
      <nav class="flex items-center md:h-16 h-[3.5rem] pl-2 px-4">
        <RuiButton
          icon
          variant="text"
          class="!text-rui-text-secondary"
          @click="toggleDrawer()"
        >
          <RuiIcon name="lu-menu" />
        </RuiButton>
        <AppIndicators />
      </nav>
    </header>

    <AppSidebars />
    <div
      class="py-4 w-full transition-all min-h-[calc(100vh-64px)]"
      :class="{
        '!transition-none': pinnedDragging,
        'pl-[3.5rem]': isMini,
        'pl-[300px]': expanded,
      }"
      :style="{ paddingRight: pinnedPadding }"
    >
      <main>
        <RouterView #default="{ Component }">
          <Transition
            enter-from-class="opacity-0"
            enter-to-class="opacity-1"
            enter-active-class="transition duration-300"
            leave-from-class="opacity-1"
            leave-to-class="opacity-0"
            leave-active-class="transition duration-100 h-0"
          >
            <div
              v-if="!logged"
              class="fixed top-0 left-0 w-full h-full bg-white dark:bg-rui-grey-900 z-[999] flex items-center justify-center"
            >
              <RuiProgress
                thickness="2"
                color="primary"
                variant="indeterminate"
                circular
              />
            </div>
            <component
              :is="Component"
              v-else
            />
          </Transition>
        </RouterView>
      </main>

      <Transition
        enter-from-class="opacity-0"
        enter-to-class="opacity-1"
        enter-active-class="transition duration-300"
        leave-from-class="opacity-1"
        leave-to-class="opacity-0"
        leave-active-class="transition duration-100"
      >
        <RuiButton
          v-if="shouldShowScrollToTopButton"
          color="primary"
          class="fixed bottom-4 right-4 z-[6]"
          variant="fab"
          icon
          @click="scrollToTop()"
        >
          <RuiIcon name="lu-arrow-up" />
        </RuiButton>
      </Transition>
    </div>
  </div>
</template>
