<template>
  <td v-if="visible" class="table-expand-container" :colspan="colspan">
    <div class="py-4">
      <div v-if="$scopedSlots.title" class="text-h6 mb-4">
        <slot name="title" />
      </div>
      <v-sheet outlined rounded :class="padded ? 'pa-4' : null">
        <slot />
      </v-sheet>
    </div>
  </td>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'TableExpandContainer',
  props: {
    visible: { required: true, type: Boolean },
    colspan: { required: true, type: Number },
    padded: { required: false, type: Boolean, default: true }
  }
});
</script>

<style scoped lang="scss">
.table-expand-container {
  background-color: var(--v-rotki-light-grey-base) !important;
}
</style>
