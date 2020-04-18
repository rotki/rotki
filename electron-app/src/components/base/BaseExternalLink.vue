<template>
  <a
    :href="$interop.isPackaged ? undefined : href"
    target="_blank"
    @click="$interop.isPackaged ? openLink() : undefined"
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
