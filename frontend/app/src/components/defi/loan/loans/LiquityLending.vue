<template>
  <div />
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { LiquityLoan } from '@/store/defi/liquity/types';

export default defineComponent({
  name: 'LiquityLending',
  props: {
    loan: {
      required: true,
      type: Object as PropType<LiquityLoan>
    }
  }
});
</script>
