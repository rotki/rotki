<script setup lang="ts">
import { Chart, registerables } from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';

const visibilityStore = useAreaVisibilityStore();
const { showDrawer, isMini } = storeToRefs(visibilityStore);

const { appBarColor } = useTheme();
const { mobile } = useDisplay();

const small = computed(() => get(showDrawer) && get(isMini));
const expanded = computed(
  () => get(showDrawer) && !get(isMini) && !get(mobile)
);
const { overall } = storeToRefs(useStatisticsStore());
const { logged } = storeToRefs(useSessionAuthStore());

const { updateTray } = useInterop();

const toggleDrawer = visibilityStore.toggleDrawer;

onMounted(() => {
  set(showDrawer, !get(mobile));
});

watch(overall, overall => {
  if (overall.percentage === '-') {
    return;
  }
  updateTray(overall);
});

onBeforeMount(() => {
  Chart.defaults.font.family = 'Roboto';
  Chart.register(...registerables);
  Chart.register(zoomPlugin);
});

const scrollToTop = () => {
  document.body.scrollTo(0, 0);
};

const { y: scrollY } = useScroll(document.body);

const shouldShowScrollToTopButton: ComputedRef<boolean> = computed(
  () => get(scrollY) > 200
);
</script>

<template>
  <div class="app__content rotki-light-grey">
    <div
      v-if="!logged"
      class="fixed top-0 left-0 w-full h-full bg-white/[0.3] z-[999] flex items-center justify-center"
    >
      <RuiProgress
        thickness="2"
        color="primary"
        variant="indeterminate"
        circular
      />
    </div>
    <NotificationPopup />
    <AppDrawer />

    <VAppBar
      app
      fixed
      clipped-left
      flat
      :color="appBarColor"
      class="app__app-bar"
    >
      <VAppBarNavIcon
        class="secondary--text text--lighten-4"
        @click="toggleDrawer()"
      />
      <AppIndicators />
    </VAppBar>
    <AppSidebars />
    <div
      class="app-main"
      :class="{
        small,
        expanded
      }"
    >
      <VMain>
        <RouterView />
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
          class="fixed bottom-4 right-4 z-[9999]"
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
      padding-left: 56px;
    }

    &.expanded {
      padding-left: 300px;
    }
  }
}
</style>
