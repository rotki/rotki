<template>
  <svg
    viewBox="0 0 229.8 207.6"
    xmlns="http://www.w3.org/2000/svg"
    :class="{
      [$style.opacity]: !dark,
      [$style.icon]: true
    }"
  >
    <g>
      <path
        d="M181.1,31.6l-45.9,18.2H92.5L48.7,31.4l9.9,60.1L49.1,124L74,138.9c11.8,7,22.3,15.9,31.4,26.2l9.7,11.1
    l10.2-11.7c8.7-10,18.9-18.6,30.2-25.5l24.4-15l-8.8-32.5L181.1,31.6z M150.8,133c-8.3,5.1-16,11.2-23,17.9l-8.5-9.2L150.8,133z
     M110.5,141.6l-8.3,9.2c-7-6.7-14.8-12.6-23.1-17.7L110.5,141.6z M102.3,131.6l-44.1-12l6-20.6L102.3,131.6z M85.7,55.2L64.8,82.5
    l-6.4-38.8L85.7,55.2z M157.2,95.5l-42.3,36.9L71.8,95.5H157.2z M70.2,87.9l23.4-30.6h40.6l26,30.6H70.2z M165.2,98.5l5.7,21.1
    l-43.6,12L165.2,98.5z M171.4,43.5L165,82l-22.8-26.8L171.4,43.5z"
        :fill="color"
      />
    </g>
  </svg>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'FOXIcon',
  props: {},
  computed: {
    dark(): boolean {
      return this.$vuetify.theme.dark;
    },
    color(): string {
      return this.dark ? '#ffffff' : '#131E29';
    }
  }
});
</script>

<style module>
.opacity {
  opacity: 1;
}

.icon {
  width: 40px;
  height: 44px;
}
</style>
