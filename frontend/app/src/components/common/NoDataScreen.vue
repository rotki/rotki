<template>
  <div
    class="d-flex flex-column align-center"
    :class="{
      [$style.empty]: true,
      'pa-2 mt-2': $vuetify.breakpoint.xsOnly
    }"
    :style="`height: calc(100vh - ${top + 64}px);`"
  >
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
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref } from '@vue/composition-api';
import { useProxy } from '@/composables/common';

export default defineComponent({
  setup() {
    const top = ref(0);
    const proxy = useProxy();
    onMounted(() => {
      const { top: topBound } = proxy.$el.getBoundingClientRect();
      top.value = topBound;
    });

    return {
      top
    };
  }
});
</script>

<style module lang="scss">
.logo {
  padding: 80px;
  border-radius: 50%;
  background-color: var(--v-rotki-light-grey-darken1);
}

.empty {
  height: 100%;
}
</style>
