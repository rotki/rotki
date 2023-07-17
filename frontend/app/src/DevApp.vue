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
      <VBtn icon :to="Routes.DASHBOARD">
        <VIcon>mdi-home</VIcon>
      </VBtn>
      <VSpacer />
      <span> {{ resetState }}</span>
      <VBtn icon class="ml-2" @click="reset()">
        <VIcon>mdi-delete</VIcon>
      </VBtn>
    </VAppBar>
    <VMain>
      <VContainer>
        <RouterView />
      </VContainer>
    </VMain>
  </VApp>
</template>
