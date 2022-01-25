<template>
  <div class="loading">
    <span v-for="i in 3" :key="i" v-text="char" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'Loading',
  setup() {
    const char = '.';
    return { char };
  }
});
</script>

<style scoped lang="scss">
@import '~@/scss/loading.scss';
</style>
