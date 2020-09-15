<template>
  <v-app id="rotki">
    <v-app-bar app fixed>
      <v-btn icon @click="refresh()">
        <v-icon>mdi-reload</v-icon>
      </v-btn>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>
<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';

@Component({})
export default class DevApp extends Vue {
  refresh() {
    sessionStorage.removeItem('vuex');
    window.location.reload();
  }
}
</script>
