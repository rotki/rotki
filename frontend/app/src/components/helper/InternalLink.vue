<script lang="ts" setup>
import { type Location } from 'vue-router/types/router';

defineOptions({
  inheritAttrs: false
});

const props = withDefaults(
  defineProps<{
    to: string | Location;
    exact?: boolean;
    activeClass?: string;
    exactActiveClass?: string;
    replace?: boolean;
  }>(),
  {
    exact: false,
    replace: false,
    activeClass: '',
    exactActiveClass: ''
  }
);

const rootAttrs = useAttrs();
</script>

<template>
  <router-link
    #default="{ href, navigate, isActive, isExactActive }"
    custom
    v-bind="props"
  >
    <a
      :class="{
        [`${activeClass}`]: isActive,
        [`${exactActiveClass}`]: isExactActive
      }"
      :href="href"
      v-bind="rootAttrs"
      @click.exact="navigate($event)"
      @click.meta.prevent
      @click.ctrl.prevent
      @click.shift.prevent
    >
      <slot />
    </a>
  </router-link>
</template>
