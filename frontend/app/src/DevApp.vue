<template>
  <v-app id="rotki">
    <v-app-bar app fixed>
      <v-btn icon to="/">
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
<script lang="ts">
import { defineComponent } from '@vue/composition-api';

const DevApp = defineComponent({
  name: 'DevApp',
  setup() {
    const reset = () => {
      sessionStorage.removeItem('vuex');
      window.location.reload();
    };
    return {
      resetState: 'Reset State ->',
      reset
    };
  }
});

export default DevApp;
</script>
