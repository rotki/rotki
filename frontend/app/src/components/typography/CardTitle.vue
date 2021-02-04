<template>
  <div class="card-title">
    <slot />
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class CardTitle extends Vue {}
</script>

<style scoped lang="scss">
.card-title {
  font-size: 14px;
  line-height: 17px;
  /* identical to box height */

  text-transform: uppercase;

  color: #447178;
}
</style>
