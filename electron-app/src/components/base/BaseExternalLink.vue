<template>
  <a
    :href="$interop ? undefined : href"
    target="_blank"
    @click="$interop ? openLink() : undefined"
  >
    <slot></slot>
  </a>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class BaseExternalLink extends Vue {
  @Prop({ required: true })
  href!: string;

  openLink() {
    this.$interop.openUrl(this.href);
  }
}
</script>

<style scoped></style>
