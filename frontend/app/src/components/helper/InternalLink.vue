<script lang="ts" setup>
import type { RouteLocationRaw } from 'vue-router';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    to: RouteLocationRaw;
    exact?: boolean;
    activeClass?: string;
    exactActiveClass?: string;
    replace?: boolean;
  }>(),
  {
    exact: false,
    replace: false,
    activeClass: '',
    exactActiveClass: '',
  },
);

const rootAttrs = useAttrs();
const css = useCssModule();
</script>

<template>
  <RouterLink
    #default="{ href, navigate, isActive, isExactActive }"
    custom
    v-bind="props"
  >
    <a
      :class="{
        [`${activeClass}`]: isActive,
        [`${exactActiveClass}`]: isExactActive,
      }"
      :href="href"
      v-bind="rootAttrs"
      @click.exact="navigate($event)"
      @click.meta.prevent
      @click.ctrl.prevent
      @click.shift.prevent
    >
      <RuiButton
        variant="text"
        color="primary"
        :class="css.button"
      >
        <slot />
      </RuiButton>
    </a>
  </RouterLink>
</template>

<style lang="scss" module>
.button {
  @apply inline text-[1em] p-0 px-0.5 -mx-0.5 #{!important};
  font-weight: inherit !important;

  span {
    @apply underline;
  }
}
</style>
