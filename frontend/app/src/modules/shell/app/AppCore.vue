<script setup lang="ts">
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import NotificationPopup from '@/modules/core/notifications/NotificationPopup.vue';
import SettingsSuggestionsDialog from '@/modules/settings/suggestions/SettingsSuggestionsDialog.vue';
import { useSettingsSuggestions } from '@/modules/settings/suggestions/use-settings-suggestions';
import { useSuggestionsStore } from '@/modules/settings/suggestions/use-suggestions-store';
import AppDrawer from '@/modules/shell/app/AppDrawer.vue';
import AppIndicators from '@/modules/shell/app/AppIndicators.vue';
import AppSidebars from '@/modules/shell/app/AppSidebars.vue';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useCoreScroll } from '@/modules/shell/layout/use-core-scroll';
import { initGraph } from '@/modules/statistics/init-graph';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

const { t } = useI18n({ useScope: 'global' });

const visibilityStore = useAreaVisibilityStore();
const { expanded, isMini, pinnedDragging, pinnedWidth, showPinned } = storeToRefs(visibilityStore);
const { overall } = storeToRefs(useStatisticsStore());
const { logged } = storeToRefs(useSessionAuthStore());
const { connected } = storeToRefs(useMainStore());
const { toggleDrawer } = visibilityStore;

/**
 * The blocking overlay covers two situations, not one.
 *
 * Signing out is the obvious one. The other is a backend that is deliberately
 * down: every restart path clears `connected` before bouncing the tree, and
 * until it comes back the page behind is inert — its data is stale and every
 * request it makes fails. Leaving it visible and interactive for the whole
 * window (seconds, for a core restart) reads as a frozen app rather than a
 * deliberate operation.
 */
const busy = computed<boolean>(() => !get(logged) || !get(connected));

/**
 * What the overlay says while the app is busy.
 *
 * @remarks
 * Follows `logged` rather than assuming a sign-out: it stays true across a restart that keeps the
 * session, which is what the desktop settings form does, and what the asset-update flows do until
 * the moment they log out.
 */
const busyMessage = computed<string>(() =>
  get(logged) ? t('connection_loading.restarting') : t('connection_loading.logging_out'),
);

const { updateTray } = useInterop();
const { scrollToTop, shouldShowScrollToTopButton } = useCoreScroll();

const { isXlAndDown } = useBreakpoint();
const { applySelected, dismissAll } = useSettingsSuggestions();
const suggestionsStore = useSuggestionsStore();

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
  <div>
    <NotificationPopup />
    <SettingsSuggestionsDialog
      v-model="suggestionsStore.showSuggestionsDialog"
      :suggestions="suggestionsStore.pendingSuggestions"
      @apply="applySelected($event)"
      @dismiss="dismissAll()"
    />
    <AppDrawer />

    <header
      class="fixed top-0 left-0 w-full bg-white dark:bg-dark-elevated md:h-16 h-[3.5rem] border-b border-rui-grey-300 dark:border-rui-grey-800"
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
              v-if="busy"
              class="fixed top-0 left-0 w-full h-full bg-white dark:bg-rui-grey-900 z-[999] flex items-center justify-center"
            >
              <div class="flex flex-col gap-4 justify-center items-center">
                <RuiProgress
                  color="primary"
                  variant="indeterminate"
                  circular
                  size="48"
                />
                <p
                  class="mb-0 text-rui-text-secondary text-center"
                  data-testid="app-busy-message"
                >
                  {{ busyMessage }}
                </p>
              </div>
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
          size="lg"
          icon
          @click="scrollToTop()"
        >
          <RuiIcon name="lu-arrow-up" />
        </RuiButton>
      </Transition>
    </div>
  </div>
</template>
