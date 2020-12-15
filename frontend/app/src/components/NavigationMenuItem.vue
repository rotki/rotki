<template>
  <div class="d-flex flex-grow-1">
    <v-tooltip v-if="showTooltips" right>
      <template #activator="{ on }">
        <v-list-item-icon v-on="on">
          <crypto-icon v-if="!!cryptoIcon" :symbol="cryptoIcon" size="24px" />
          <v-icon v-else>{{ icon }}</v-icon>
        </v-list-item-icon>
      </template>
      <span>{{ text }}</span>
    </v-tooltip>
    <v-list-item-icon v-else>
      <crypto-icon v-if="!!cryptoIcon" :symbol="cryptoIcon" size="24px" />
      <v-icon v-else>{{ icon }}</v-icon>
    </v-list-item-icon>
    <v-list-item-content class="d-flex flex-grow-1">
      <v-list-item-title>{{ text }}</v-list-item-title>
    </v-list-item-content>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';

@Component({})
export default class NavigationMenuItem extends Vue {
  @Prop({ required: false, type: Boolean, default: false })
  showTooltips!: boolean;
  @Prop({ required: false, type: String, default: '' })
  icon!: string;
  @Prop({ required: false, type: String, default: '' })
  cryptoIcon!: string;
  @Prop({ required: true, type: String })
  text!: string;
}
</script>

<style scoped lang="scss"></style>
