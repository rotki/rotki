<template>
  <v-card class="stat-card">
    <v-card-title>
      {{ title }}
      <v-spacer v-if="locked"></v-spacer>
      <premium-lock v-if="locked"></premium-lock>
    </v-card-title>
    <v-card-text>
      <slot v-if="!locked"></slot>
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
  @Prop({ required: true })
  title!: string;
  @Prop({ required: false, type: Boolean, default: false })
  locked!: boolean;
}
</script>

<style scoped lang="scss">
.stat-card {
  width: 100%;
  padding-bottom: 12px;
  padding-left: 12px;
  padding-right: 12px;
  min-height: 130px;
  ::v-deep {
    .v-card__title {
      font-size: 16px;
      color: rgba(100, 100, 100, 0.98);
    }
    .v-card__text {
      color: rgba(56, 56, 56, 0.95);
      padding-top: 12px;
      font-weight: 500;
      font-size: 32px;
    }
  }
}
</style>
