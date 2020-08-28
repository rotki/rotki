<template>
  <v-card class="stat-card">
    <v-card-title>
      <v-img
        v-if="protocolIcon"
        contain
        alt="Protocol Logo"
        max-height="32px"
        :src="protocolIcon"
      />
      <span v-if="title">
        {{ title }}
      </span>
      <v-spacer v-if="locked" />
      <premium-lock v-if="locked" />
    </v-card-title>
    <v-card-text class="flex">
      <span v-if="!locked && loading">
        <v-progress-linear indeterminate color="primary" />
      </span>
      <slot v-else-if="!locked" />
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
  @Prop({ required: false, type: String })
  protocolIcon!: string;
}
</script>

<style scoped lang="scss">
.stat-card {
  width: 100%;
  min-height: 130px;

  ::v-deep {
    .v-card {
      &__text {
        padding-top: 12px;
        font-size: 1em;
      }
    }
  }
}
</style>
