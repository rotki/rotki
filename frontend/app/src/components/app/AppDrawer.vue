<script setup lang="ts">
const { isMini, showDrawer } = storeToRefs(useAreaVisibilityStore());
const { appVersion } = toRefs(useMainStore());
const { appBarColor } = useTheme();

const remoteDrawerImage =
  'https://raw.githubusercontent.com/rotki/data/main/assets/icons/drawer_logo.png';

const { t } = useI18n();
</script>

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
    <div v-if="!isMini" class="app__logo">
      <rotki-logo height="150px" :url="remoteDrawerImage" />
    </div>
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

<style scoped lang="scss">
.app {
  &__logo {
    margin-bottom: 15px;
    margin-top: 15px;

    &-mini {
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
  box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);

  &--is-mobile {
    padding-top: 60px !important;
  }
}
</style>
