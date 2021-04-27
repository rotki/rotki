<template>
  <div class="card-title" :class="dark ? 'theme--dark' : null">
    <slot />
  </div>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import ThemeMixin from '@/mixins/theme-mixin';

@Component({})
export default class CardTitle extends Mixins(ThemeMixin) {}
</script>

<style scoped lang="scss">
.card-title {
  font-size: 14px;
  line-height: 17px;
  /* identical to box height */

  text-transform: uppercase;

  color: #447178;
  height: 24px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.theme {
  &--dark {
    .card-title {
      color: #62a4af;
    }
  }
}
</style>
