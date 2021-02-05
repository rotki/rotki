<template>
  <v-card class="mt-8">
    <v-card-title>
      <card-title><slot name="title" /></card-title>
    </v-card-title>
    <v-card-subtitle v-if="$slots.subtitle">
      <slot name="subtitle" />
    </v-card-subtitle>
    <v-card-text>
      <slot />
    </v-card-text>
  </v-card>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class SettingCategory extends Vue {}
</script>
