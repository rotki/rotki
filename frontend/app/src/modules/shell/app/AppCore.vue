<script setup lang="ts">
import { RuiButton, RuiIcon, RuiProgress, useBreakpoint } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, onBeforeMount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import NotificationPopup from '@/modules/core/notifications/NotificationPopup.vue';
import AppDrawer from '@/modules/shell/app/AppDrawer.vue';
import AppFloatingDock from '@/modules/shell/app/AppFloatingDock.vue';
import AppIndicators from '@/modules/shell/app/AppIndicators.vue';
import AppSettingsSuggestions from '@/modules/shell/app/AppSettingsSuggestions.vue';
import AppSidebars from '@/modules/shell/app/AppSidebars.vue';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
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

const route = useRoute();

/** The height of the dock's pill; the expanded panel overlays the page and reserves no room. */
const dockHeight = ref<number>(0);
const { updateTray } = useInterop();

const { isXlAndDown } = useBreakpoint();

const pinnedPadding = computed<string | undefined>(() => {
  if (get(showPinned) && !get(isXlAndDown))
    return `calc(${get(pinnedWidth)}px - 100vw + 100%)`;

  return undefined;
});

/**
 * Room below the page content while the task dock shows, its height plus its 1rem offset and a 1rem
 * gap, so the end of a page that just fits, such as a table's last row and its actions, can scroll
 * clear of the dock instead of sitting under it.
 */
const dockPadding = computed<string | undefined>(() => {
  if (route.meta.scrollsItself)
    return undefined;
  const height = get(dockHeight);
  return height > 0 ? `calc(${height}px + 2rem)` : undefined;
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
    <AppSettingsSuggestions />
    <AppDrawer />

    <header
      class="fixed top-0 left-0 w-full bg-rui-surface md:h-16 h-14 border-b border-rui-grey-300 dark:border-rui-grey-800"
    >
      <nav class="flex items-center md:h-16 h-14 pl-2 px-4">
        <RuiButton
          icon
          variant="text"
          class="text-rui-text-secondary!"
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
        'transition-none!': pinnedDragging,
        'pl-14': isMini,
        'pl-75': expanded,
      }"
      :style="{ paddingRight: pinnedPadding, paddingBottom: dockPadding }"
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
              class="fixed top-0 left-0 w-full h-full bg-white dark:bg-rui-grey-900 z-999 flex items-center justify-center"
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

      <AppFloatingDock v-model:dock-height="dockHeight" />
    </div>
  </div>
</template>
