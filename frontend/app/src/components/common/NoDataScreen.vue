<template>
  <full-size-content>
    <v-row align="center" justify="center">
      <v-col cols="auto" :class="$style.logo">
        <slot name="logo">
          <v-img
            contain
            :max-width="$vuetify.breakpoint.mobile ? '100px' : '200px'"
            :src="require('@/assets/images/rotkehlchen_no_text.png')"
          />
        </slot>
      </v-col>
    </v-row>
    <v-row class="text-center">
      <v-col>
        <div v-if="$slots.title" class="text-h5">
          <slot name="title" />
        </div>
        <slot />
      </v-col>
    </v-row>
  </full-size-content>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import FullSizeContent from '@/components/common/FullSizeContent.vue';

export default defineComponent({
  name: 'NoDataScreen',
  components: { FullSizeContent }
});
</script>

<style module lang="scss">
.logo {
  padding: 80px;
  border-radius: 50%;
  background-color: var(--v-rotki-light-grey-darken1);
}
</style>
