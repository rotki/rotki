<template>
  <v-navigation-drawer
    v-model="showDrawer"
    width="300"
    class="app__navigation-drawer"
    fixed
    :mini-variant="isMini"
    :color="appBarColor"
    clipped
    app
  >
    <div v-if="!isMini" class="text-center app__logo" />
    <div v-else class="app__logo-mini">
      {{ t('app.name') }}
    </div>
    <navigation-menu :is-mini="isMini" />
    <v-spacer />
    <div
      v-if="!isMini"
      class="my-2 text-center px-2 app__navigation-drawer__version"
    >
      <span class="text-overline">
        <v-divider class="mx-3 my-1" />
        {{ appVersion }}
      </span>
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { useTheme } from '@/composables/common';
import { useMainStore } from '@/store/main';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const NavigationMenu = defineAsyncComponent(
  () => import('@/components/NavigationMenu.vue')
);

const { isMini, showDrawer } = storeToRefs(useAreaVisibilityStore());
const { appVersion } = toRefs(useMainStore());
const { appBarColor } = useTheme();

const { t } = useI18n();
</script>

<style scoped lang="scss">
.app {
  &__logo {
    min-height: 150px;
    margin-bottom: 15px;
    margin-top: 15px;
    background: url(/assets/images/rotkehlchen_no_text.png) no-repeat center;
    background-size: contain;
  }

  &__logo-mini {
    text-align: center;
    align-self: center;
    font-size: 3em;
    font-weight: bold;
    height: 150px;
    width: 64px;
    writing-mode: vertical-lr;
    transform: rotate(-180deg);
    margin-bottom: 15px;
    margin-top: 15px;
  }

  &__navigation-drawer {
    padding-bottom: 48px;

    &__version {
      position: fixed;
      bottom: 0;
      width: 100%;
    }
  }
}

.v-navigation-drawer {
  &--is-mobile {
    padding-top: 60px !important;
  }
}

:deep() {
  .v-navigation-drawer {
    box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);

    &__border {
      background-color: transparent !important;
    }
  }
}
</style>
