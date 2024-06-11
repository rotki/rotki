<script setup lang="ts">
import { Chart, registerables } from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';
import { useBreakpoint, useRotkiTheme } from '@rotki/ui-library-compat';

const visibilityStore = useAreaVisibilityStore();
const { showDrawer, isMini } = storeToRefs(visibilityStore);

const { isDark } = useRotkiTheme();
const { isXlAndDown } = useBreakpoint();

const expanded = logicAnd(showDrawer, logicNot(isXlAndDown));
const { overall } = storeToRefs(useStatisticsStore());
const { logged } = storeToRefs(useSessionAuthStore());

const { updateTray } = useInterop();

const toggleDrawer = visibilityStore.toggleDrawer;

onMounted(() => {
  set(showDrawer, !get(isXlAndDown));
});

watch(overall, (overall) => {
  if (overall.percentage === '-')
    return;

  updateTray(overall);
});

onBeforeMount(() => {
  Chart.defaults.font.family = 'Roboto';
  Chart.register(...registerables);
  Chart.register(zoomPlugin);
});

function scrollToTop() {
  document.body.scrollTo(0, 0);
}

const { y: scrollY } = useScroll(document.body);

const shouldShowScrollToTopButton: ComputedRef<boolean> = computed(
  () => get(scrollY) > 200,
);
</script>

<template>
  <div class="app__content rotki-light-grey">
    <NotificationPopup />
    <AppDrawer />

    <VAppBar
      app
      fixed
      clipped-left
      flat
      :color="isDark ? null : 'white'"
      class="app__app-bar"
    >
      <VAppBarNavIcon
        class="!text-rui-text-secondary"
        @click="toggleDrawer()"
      />
      <AppIndicators />
    </VAppBar>
    <AppSidebars />
    <div
      class="app-main"
      :class="{
        small: isMini,
        expanded,
      }"
    >
      <VMain>
        <Transition
          v-if="!logged"
          enter-class="opacity-0"
          enter-to-class="opacity-1"
          enter-active-class="transition duration-300"
          leave-class="opacity-1"
          leave-to-class="opacity-0"
          leave-active-class="transition duration-100"
        >
          <div
            class="fixed top-0 left-0 w-full h-full bg-white z-[999] flex items-center justify-center"
          >
            <RuiProgress
              thickness="2"
              color="primary"
              variant="indeterminate"
              circular
            />
          </div>
        </Transition>
        <RouterView v-else />
      </VMain>

      <Transition
        enter-class="opacity-0"
        enter-to-class="opacity-1"
        enter-active-class="transition duration-300"
        leave-class="opacity-1"
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
          <RuiIcon name="arrow-up-line" />
        </RuiButton>
      </Transition>
    </div>
  </div>
</template>

<style scoped lang="scss">
.v-main {
  padding: 0 !important;
}

.v-app-bar {
  &::after {
    height: 1px;
    display: block;
    width: 100%;
    content: '';
    border-bottom: var(--v-rotki-light-grey-darken1) solid thin;
  }
}

.app {
  &__app-bar {
    &__button {
      i {
        &:focus {
          color: var(--v-primary-base) !important;
        }
      }

      button {
        &:focus {
          color: var(--v-primary-base) !important;
        }
      }
    }
  }

  &-main {
    padding-top: 1rem;
    padding-bottom: 4rem;
    width: 100%;
    min-height: calc(100vh - 64px);

    &.small {
      @apply pl-[3.5rem];
    }

    &.expanded {
      padding-left: 300px;
    }
  }
}
</style>
