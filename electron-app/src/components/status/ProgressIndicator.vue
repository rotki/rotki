<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-menu id="notification-indicator" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-badge>
        <v-btn color="primary" dark icon text v-on="on">
          <v-icon class="top-loading-icon">
            fa fa-circle-o-notch fa-spin fa-fw
          </v-icon>
          <v-icon>fa fa-caret-down</v-icon>
        </v-btn>
      </v-badge>
    </template>
    <v-layout column class="popup">
      <ul class="dropdown-menu dropdown-tasks"></ul>
    </v-layout>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class ProgressIndicator extends Vue {}
</script>

<style scoped lang="scss"></style>
