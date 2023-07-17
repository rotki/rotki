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
    padding-bottom: 1rem;
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
