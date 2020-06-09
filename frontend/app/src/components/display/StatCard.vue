<template>
  <v-card class="stat-card">
    <v-card-title>
      {{ title }}
      <v-spacer v-if="locked"></v-spacer>
      <premium-lock v-if="locked"></premium-lock>
    </v-card-title>
    <v-card-text class="flex">
      <span v-if="!locked && loading">
        <v-progress-linear indeterminate color="primary"></v-progress-linear>
      </span>
      <slot v-else-if="!locked"></slot>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import PremiumLock from '@/components/helper/PremiumLock.vue';

@Component({
  components: { PremiumLock }
})
export default class StatCard extends Vue {
  @Prop({ required: false })
  title!: string;
  @Prop({ required: false, type: Boolean, default: false })
  locked!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  loading!: boolean;
}
</script>

<style scoped lang="scss">
.stat-card {
  width: 100%;
  min-height: 130px;
  ::v-deep {
    .v-card__text {
      padding-top: 12px;
      font-size: 1em;
    }
  }
}
</style>
