<template>
  <a href="#" @click="openLink()"><slot></slot></a>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';

@Component({})
export default class ExternalLink extends Vue {
  @Prop({ required: true })
  url!: string;

  openLink() {
    this.$interop.openUrl(this.url);
  }
}
</script>
