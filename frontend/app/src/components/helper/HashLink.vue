<template>
  <div>
    <span>{{ text | truncateAddress }}</span>
    <v-btn
      x-small
      icon
      width="20px"
      color="red"
      class="primary--text grey lighten-4 ml-2"
      @click="copyText(text)"
    >
      <v-icon x-small>
        fa fa-clone
      </v-icon>
    </v-btn>
    <v-btn
      x-small
      icon
      width="20px"
      color="red"
      class="primary--text grey lighten-4 ml-1 mr-2"
      @click="openLink()"
    >
      <v-icon x-small>
        fa fa-external-link
      </v-icon>
    </v-btn>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class HashLink extends Vue {
  @Prop({ required: true, type: String })
  text!: string;
  @Prop({
    required: false,
    type: String,
    default: 'https://etherscan.io/address/'
  })
  baseUrl!: string;

  copyText(text: string) {
    navigator.clipboard.writeText(text);
  }

  openLink() {
    const href = this.baseUrl + this.text;
    this.$interop.openUrl(href);
  }
}
</script>

<style scoped lang="scss"></style>
