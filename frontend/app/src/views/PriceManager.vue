<template>
  <price-management />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import PriceManagement from '@/components/price-manager/PriceManagement.vue';

export default defineComponent({
  components: { PriceManagement }
});
</script>

<style scoped lang="scss"></style>
