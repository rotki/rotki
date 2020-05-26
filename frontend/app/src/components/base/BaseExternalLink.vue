<template>
  <a
    :href="$interop.isPackaged ? undefined : href"
    target="_blank"
    @click="$interop.isPackaged ? openLink() : undefined"
  >
    <span v-if="truncate">
      {{ text | truncateAddress }}
    </span>
    <span v-else>
      {{ text }}
    </span>
  </a>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class BaseExternalLink extends Vue {
  @Prop({ required: true })
  href!: string;
  @Prop({ required: true })
  text!: string;
  @Prop({ required: false, type: Boolean, default: false })
  truncate!: boolean;

  openLink() {
    this.$interop.openUrl(this.href);
  }
}
</script>

<style scoped></style>
