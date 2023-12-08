<script setup lang="ts">
const { isMini, showDrawer } = storeToRefs(useAreaVisibilityStore());
const { appVersion } = storeToRefs(useMainStore());
const { appBarColor } = useTheme();

const remoteDrawerImage =
  'https://raw.githubusercontent.com/rotki/data/main/assets/icons/drawer_logo.png';
</script>

<template>
  <VNavigationDrawer
    v-model="showDrawer"
    width="300"
    class="app__navigation-drawer"
    fixed
    :mini-variant="isMini"
    :color="appBarColor"
    clipped
    app
  >
    <div class="app__logo" :class="{ 'app__logo--mini': isMini }">
      <RuiLogo :text="!isMini" :custom-src="remoteDrawerImage" />
    </div>
    <NavigationMenu :is-mini="isMini" />
    <div class="grow" />
    <div
      v-if="!isMini"
      class="my-2 text-center px-2 app__navigation-drawer__version"
    >
      <span class="text-overline">
        <RuiDivider class="mx-3 my-1" />
        {{ appVersion }}
      </span>
    </div>
  </VNavigationDrawer>
</template>

<style scoped lang="scss">
.app {
  &__logo {
    padding: 1.5rem 1rem;

    &--mini {
      padding: 1rem 0.5rem;
      margin-bottom: 1rem;

      > div {
        height: 32px;
        display: flex;
        justify-content: center;
      }
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
  &--is-mobile {
    padding-top: 60px !important;
  }
}
</style>
