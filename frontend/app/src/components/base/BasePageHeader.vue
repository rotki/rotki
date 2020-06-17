<template>
  <v-row class="base-page-header">
    <v-col class="mx-4">
      <div class="base-page-header__text">{{ text }}</div>
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

<style lang="scss" scoped>
.base-page-header {
  &__text {
    font-size: 3em;
    font-weight: bold;
  }
}
</style>
