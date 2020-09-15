<template>
  <v-app id="rotki">
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>
<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';

@Component({})
export default class DevApp extends Vue {}
</script>
