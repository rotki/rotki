<template>
  <v-chip
    small
    :color="`${color} lighten-5`"
    :text-color="color"
    class="font-weight-black rounded py-0 px-2 text-overline"
    v-bind="$attrs"
    v-on="$listeners"
  >
    <slot />
  </v-chip>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'BadgeDisplay',
  props: {
    color: { required: false, type: String, default: 'grey-darken' }
  }
});
</script>
