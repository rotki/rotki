<template>
  <div
    class="d-flex justify-space-between py-1"
    :class="{
      'font-weight-medium': medium
    }"
  >
    <div>
      {{ title }}
    </div>
    <div>
      <slot />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'LoanRow',
  props: {
    title: { required: false, type: String, default: '' },
    medium: { required: false, type: Boolean, default: true }
  }
});
</script>
