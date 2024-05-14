<script setup lang="ts">
const { isMini, showDrawer } = storeToRefs(useAreaVisibilityStore());
const { appVersion } = storeToRefs(useMainStore());
const { appBarColor } = useTheme();
</script>

<template>
  <VNavigationDrawer
    v-model="showDrawer"
    width="300"
    class="app__navigation-drawer"
    :class="{ 'app__navigation-drawer--mini': isMini }"
    fixed
    :mini-variant="isMini"
    :mobile-breakpoint="1280"
    :color="appBarColor"
    clipped
    app
  >
    <div
      class="app__logo"
      :class="{ 'app__logo--mini': isMini }"
    >
      <RotkiLogo
        :text="!isMini"
        :size="isMini ? 1.625 : 3"
      />
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
    padding-bottom: 3rem;

    &__version {
      position: fixed;
      bottom: 0;
      width: 100%;
    }
  }
}
</style>
