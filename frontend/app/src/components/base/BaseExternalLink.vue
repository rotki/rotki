<template>
  <a
    :href="$interop.isPackaged ? undefined : href"
    target="_blank"
    @click="$interop.isPackaged ? openLink() : undefined"
  >
    {{ displayText }}
  </a>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { truncateAddress } from '@/filters';

@Component({})
export default class BaseExternalLink extends Vue {
  @Prop({ required: true })
  href!: string;
  @Prop({ required: true })
  text!: string;
  @Prop({ required: false, type: Boolean, default: false })
  truncate!: boolean;

  get displayText(): string {
    return this.truncate ? truncateAddress(this.text) : this.text;
  }

  openLink() {
    this.$interop.openUrl(this.href);
  }
}
</script>
