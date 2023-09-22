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
      <RuiButton icon variant="text" :to="Routes.DASHBOARD">
        <VIcon>mdi-home</VIcon>
      </RuiButton>
      <VSpacer />
      <span> {{ resetState }}</span>
      <RuiButton icon variant="text" class="ml-2" @click="reset()">
        <VIcon>mdi-delete</VIcon>
      </RuiButton>
    </VAppBar>
    <VMain>
      <VContainer>
        <RouterView />
      </VContainer>
    </VMain>
  </VApp>
</template>
