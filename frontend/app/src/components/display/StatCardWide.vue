<template>
  <v-card class="stat-card-wide" :loading="!locked && loading">
    <v-row v-if="!locked" no-gutters>
      <v-col
        class="stat-card-wide__first-col pa-6"
        cols="12"
        :sm="colsSize[cols]"
      >
        <slot name="first-col"></slot>
      </v-col>
      <v-col
        class="stat-card-wide__second-col d-flex"
        :class="{
          'stat-card-wide__second-col--horizontal': $vuetify.breakpoint.smAndUp
        }"
        cols="12"
        :sm="colsSize[cols]"
      >
        <v-divider :vertical="$vuetify.breakpoint.smAndUp"></v-divider>
        <div class="stat-card-wide__second-col__content pa-6 flex-grow-1">
          <slot name="second-col"></slot>
        </div>
        <v-divider
          v-if="cols !== 'two'"
          :vertical="$vuetify.breakpoint.smAndUp"
        ></v-divider>
      </v-col>
      <v-col
        v-if="cols !== 'two'"
        class="stat-card-wide__third-col pa-6"
        cols="12"
        :sm="colsSize[cols]"
      >
        <slot name="third-col"></slot>
      </v-col>
      <v-col
        v-if="cols !== 'two' && cols !== 'three'"
        class="stat-card-wide__fourth-col pa-6"
        cols="12"
        :sm="colsSize[cols]"
      >
        <slot name="fourth-col"></slot>
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col cols="12" class="pa-6 text-right">
        <premium-lock></premium-lock>
      </v-col>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import PremiumLock from '@/components/helper/PremiumLock.vue';

@Component({
  components: { PremiumLock }
})
export default class StatCardWide extends Vue {
  @Prop({ required: false })
  firstCol!: string;
  @Prop({ required: false })
  secondCol!: string;
  @Prop({ required: false })
  thirdCol!: string;
  @Prop({ required: false })
  fourthCol!: string;
  @Prop({ required: false, type: Boolean, default: false })
  locked!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  loading!: boolean;
  @Prop({ required: false, type: String, default: 'three' })
  cols!: boolean;

  colsSize = {
    two: 6,
    three: 4,
    four: 3
  };
}
</script>

<style scoped lang="scss">
.stat-card-wide {
  &__second-col {
    flex-direction: column;
    &--horizontal {
      flex-direction: row;
    }
  }
}
</style>
