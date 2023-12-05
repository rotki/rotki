<script setup lang="ts">
import { Routes } from '@/router/routes';

const reset = () => {
  sessionStorage.removeItem('vuex');
  window.location.reload();
};

const resetState = 'Reset State ->';
</script>

<template>
  <VApp id="rotki">
    <VAppBar app fixed>
      <RouterLink :to="Routes.DASHBOARD">
        <RuiButton variant="text" icon>
          <RuiIcon name="home-3-line" />
        </RuiButton>
      </RouterLink>
      <VSpacer />
      <span> {{ resetState }}</span>
      <RuiButton variant="text" icon class="ml-2" @click="reset()">
        <RuiIcon name="restart-line" />
      </RuiButton>
    </VAppBar>
    <VMain>
      <VContainer>
        <RouterView />
      </VContainer>
    </VMain>
  </VApp>
</template>
