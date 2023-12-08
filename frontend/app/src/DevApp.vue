<script setup lang="ts">
import { Routes } from '@/router/routes';

const reset = () => {
  sessionStorage.removeItem('vuex');
  window.location.reload();
};

const resetState = 'Reset State';
</script>

<template>
  <div id="rotki" class="w-full h-full">
    <nav
      class="border-default bg-white dark:bg-black border-b flex gap-4 align-center fixed w-full p-2 top-0"
    >
      <RouterLink :to="Routes.DASHBOARD">
        <RuiButton variant="text" icon>
          <RuiIcon name="home-3-line" />
        </RuiButton>
      </RouterLink>
      <div class="grow" />
      <RuiButton variant="outlined" color="warning" @click="reset()">
        <template #prepend>
          <RuiIcon name="restart-line" />
        </template>
        {{ resetState }}
      </RuiButton>
    </nav>
    <div class="w-full h-full">
      <RouterView />
    </div>
  </div>
</template>
