<template>
  <fragment>
    <td v-if="offset > 0" :colspan="offset" :class="offsetClassName">
      <slot name="offset" />
    </td>
    <td v-if="visible" class="table-expand-container" :colspan="colspan">
      <div class="py-4">
        <div v-if="$scopedSlots.title" class="text-h6 mb-4">
          <slot name="title" />
        </div>
        <v-sheet
          v-if="$scopedSlots.default"
          outlined
          rounded
          :class="padded ? 'pa-4' : null"
        >
          <slot />
        </v-sheet>
        <div>
          <slot name="append" />
        </div>
      </div>
    </td>
  </fragment>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import Fragment from '@/components/helper/Fragment';

export default defineComponent({
  name: 'TableExpandContainer',
  components: { Fragment },
  props: {
    visible: { required: true, type: Boolean },
    colspan: { required: true, type: Number },
    padded: { required: false, type: Boolean, default: true },
    offset: { required: false, type: Number, default: 0 },
    offsetClassName: { required: false, type: String, default: '' }
  }
});
</script>

<style scoped lang="scss">
.table-expand-container {
  background-color: var(--v-rotki-light-grey-base) !important;
}
</style>
