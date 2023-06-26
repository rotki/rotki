<script setup lang="ts">
import { Chart, registerables } from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';

const visibilityStore = useAreaVisibilityStore();
const { showDrawer, isMini, small } = storeToRefs(visibilityStore);

const { appBarColor } = useTheme();
const { mobile } = useDisplay();

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
    <notification-popup />
    <app-drawer />

    <v-app-bar
      app
      fixed
      clipped-left
      flat
      :color="appBarColor"
      class="app__app-bar"
    >
      <v-app-bar-nav-icon
        class="secondary--text text--lighten-4"
        @click="toggleDrawer()"
      />
      <app-indicators />
    </v-app-bar>
    <app-sidebars />
    <div
      class="app-main"
      :class="{
        small,
        expanded
      }"
    >
      <v-main>
        <router-view />
      </v-main>
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
