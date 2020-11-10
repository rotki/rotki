<template>
  <div class="loading">
    <span v-for="i in 3" :key="i" v-text="char" />
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class Loading extends Vue {
  readonly char = '.';
}
</script>

<style scoped lang="scss">
@import '~@/scss/loading.scss';
</style>
