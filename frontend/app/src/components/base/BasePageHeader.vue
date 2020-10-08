<template>
  <v-row class="base-page-header" align="center">
    <v-col class="mt-4 mb-4">
      <div class="text-h3">{{ text }}</div>
    </v-col>
    <v-col cols="auto">
      <slot />
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class BaseExternalLink extends Vue {
  @Prop({ required: true })
  text!: string;
}
</script>
