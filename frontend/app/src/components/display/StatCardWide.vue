<template>
  <v-card class="stat-card-wide" :loading="!locked && loading">
    <v-row v-if="!locked" no-gutters>
      <v-col
        class="stat-card-wide__first-col pa-6"
        cols="12"
        :sm="colsSize[cols]"
      >
        <slot name="first-col" />
      </v-col>
      <v-col
        class="stat-card-wide__second-col d-flex"
        :class="{
          'stat-card-wide__second-col--horizontal': $vuetify.breakpoint.smAndUp
        }"
        cols="12"
        :sm="colsSize[cols]"
      >
        <v-divider :vertical="$vuetify.breakpoint.smAndUp" />
        <div class="stat-card-wide__second-col__content pa-6 flex-grow-1">
          <slot name="second-col" />
        </div>
        <v-divider v-if="cols > 2" :vertical="$vuetify.breakpoint.smAndUp" />
      </v-col>
      <v-col
        v-if="cols > 2"
        class="stat-card-wide__third-col pa-6"
        cols="12"
        :sm="colsSize[cols]"
      >
        <slot name="third-col" />
      </v-col>
      <v-col
        v-if="cols > 3"
        class="stat-card-wide__fourth-col pa-6"
        cols="12"
        :sm="colsSize[cols]"
      >
        <slot name="fourth-col" />
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col cols="12" class="pa-6 text-right">
        <premium-lock />
      </v-col>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import PremiumLock from '@/components/premium/PremiumLock.vue';

export default defineComponent({
  name: 'StatCardWide',

  components: { PremiumLock },
  props: {
    locked: { required: false, type: Boolean, default: false },
    loading: { required: false, type: Boolean, default: false },
    cols: { required: false, type: Number, default: 3 }
  },

  setup() {
    const colsSize = {
      2: 6,
      3: 4,
      4: 3
    };

    return {
      colsSize
    };
  }
});
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
