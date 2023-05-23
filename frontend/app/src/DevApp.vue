<script setup lang="ts">
import { Routes } from '@/router/routes';

const reset = () => {
  sessionStorage.removeItem('vuex');
  window.location.reload();
};

const resetState = 'Reset State ->';
</script>

<template>
  <v-app id="rotki">
    <v-app-bar app fixed>
      <v-btn icon :to="Routes.DASHBOARD">
        <v-icon>mdi-home</v-icon>
      </v-btn>
      <v-spacer />
      <span> {{ resetState }}</span>
      <v-btn icon class="ml-2" @click="reset()">
        <v-icon>mdi-delete</v-icon>
      </v-btn>
    </v-app-bar>
    <v-main>
      <v-container>
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>
