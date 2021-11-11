<template>
  <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" :style="style">
    <g transform="translate(1 .76303)" :fill="color" fill-rule="evenodd">
      <g transform="translate(9.554 3)">
        <path
          d="m18.448 7.8013h-3.52e-4l-0.66795 0.21091v2.5155c0 1.2627-0.83097 2.4066-2.0204 2.7816l-6.8696 2.1662v3.7285l9.0287-2.8468c2.1415-0.66689 3.42-2.5155 3.42-4.9453v-1.6683c0-1.1391-1.3056-2.444-2.8904-1.9422"
        />
        <path
          d="m4.082 6.7379 12.763-4.0239c1.3943-0.43873 2.5-0.41478 3.1676-0.33697l-1.6003-1.1686c-0.73766-0.5345-2.9873-1.7852-5.7612-0.90104l-12.125 3.8232z"
        />
        <path
          d="m23.527 17.78s2.2542-2.0461 2.2542-6.4432v-1.8605c0-2.8954-3.3341-7.5995-8.6724-5.9133l-12.664 3.9925v23.482l3.5559-1.1211v-5.7724l11.429-3.6031c2.1302-0.66478 3.9059 1.006 3.9059 2.864v2.2887c0 2.3299-2.0574 5.6337-5.2837 6.6471l-17.526 5.5256 3.5559 2.6074 15.788-4.9777c3.333-1.0602 7.0217-3.9197 7.0217-9.9907v-2.3376c0-3.6711-3.3651-5.3879-3.3651-5.3879m-5.3418-0.57464-10.184 3.2109v-10.253l10.177-3.2087c2.1246-0.66513 4.0471 1.0327 4.0471 2.7883l7.04e-4 1.6693c0 2.9204-1.5979 5.027-4.0408 5.7936"
        />
        <path
          d="m22.447 25.694v-2.2859c0-1.2915-1.2479-2.4936-2.7521-2.0179l-0.80386 0.25352v3.1647c0 1.5595-0.99928 2.9225-2.4869 3.3915l-12.848 4.0503-3.521e-4 -24.795-3.5563-2.6074v32.253l17.785-5.607c2.789-0.87921 4.6626-3.7084 4.6626-5.7992"
        />
      </g>
    </g>
  </svg>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { setupThemeCheck } from '@/composables/common';

export default defineComponent({
  name: 'BitpandaIcon',
  props: {
    width: {
      required: true,
      type: String
    }
  },
  setup(props) {
    const { width } = toRefs(props);
    const { dark } = setupThemeCheck();
    const color = computed(() => {
      const isDark = dark.value;

      return isDark ? '#fcfcfc' : '#0c0c0c';
    });

    const style = computed(() => ({
      width: width.value
    }));
    return {
      color,
      style
    };
  }
});
</script>
