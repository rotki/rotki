<template>
  <v-tooltip top open-delay="400">
    <template #activator="{ on, attrs }">
      <v-btn small v-bind="attrs" icon v-on="on" @click="copy">
        <v-icon small>mdi-content-copy</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class CopyButton extends Vue {
  @Prop({ required: true, type: String })
  value!: string;
  @Prop({ required: true, type: String })
  tooltip!: string;

  copy() {
    navigator.clipboard.writeText(this.value);
  }
}
</script>
