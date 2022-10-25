<template>
  <div class="app__content rotki-light-grey">
    <asset-update auto />
    <notification-popup />
    <app-drawer v-if="loginComplete" />

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

<script setup lang="ts">
import { Chart, registerables } from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';
import { useTheme } from '@/composables/common';
import { useInterop } from '@/electron-interop';
import { useSessionStore } from '@/store/session';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { useStatisticsStore } from '@/store/statistics';

const AppDrawer = defineAsyncComponent(
  () => import('@/components/app/AppDrawer.vue')
);
const AppSidebars = defineAsyncComponent(
  () => import('@/components/app/AppSidebars.vue')
);
const AppIndicators = defineAsyncComponent(
  () => import('@/components/app/AppIndicators.vue')
);
const AssetUpdate = defineAsyncComponent(
  () => import('@/components/status/update/AssetUpdate.vue')
);
const NotificationPopup = defineAsyncComponent(
  () => import('@/components/status/notifications/NotificationPopup.vue')
);

const { loginComplete } = storeToRefs(useSessionStore());
const visibilityStore = useAreaVisibilityStore();
const { showDrawer, isMini } = storeToRefs(visibilityStore);

const { isMobile, appBarColor } = useTheme();

const small = computed(() => get(showDrawer) && get(isMini));
const expanded = computed(
  () => get(showDrawer) && !get(isMini) && !get(isMobile)
);
const { overall } = storeToRefs(useStatisticsStore());

const { updateTray } = useInterop();

const toggleDrawer = visibilityStore.toggleDrawer;

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

<style scoped lang="scss">
:deep() {
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
}

.app {
  &__app-bar {
    :deep() {
      .v-toolbar {
        &__content {
          padding: 0 1rem;
        }
      }
    }

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
