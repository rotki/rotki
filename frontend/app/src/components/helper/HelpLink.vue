<template>
  <v-tooltip open-delay="400" top>
    <template #activator="{ attrs, on }">
      <v-btn
        icon
        :small="small"
        v-bind="attrs"
        :href="$interop.isPackaged ? undefined : url"
        target="_blank"
        v-on="on"
        @click="$interop.isPackaged ? openLink() : undefined"
      >
        <v-icon :small="small">mdi-help-circle</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class HelpLink extends Vue {
  @Prop({ required: true, type: String })
  url!: string;
  @Prop({ required: true, type: String })
  tooltip!: string;
  @Prop({ required: false, default: false, type: Boolean })
  small!: boolean;

  openLink() {
    this.$interop.openUrl(this.url);
  }
}
</script>
