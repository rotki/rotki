<template>
  <span>
    <v-btn icon @click="click">
      <v-icon :class="{ icon: true, 'icon--expanded': expanded }">
        mdi-chevron-down
      </v-icon>
    </v-btn>
  </span>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'RowExpander',
  props: {
    expanded: { required: true, type: Boolean }
  },
  emits: ['click'],
  setup(_, { emit }) {
    const click = () => emit('click');

    return {
      click
    };
  }
});
</script>
<style scoped lang="scss">
.icon {
  &--expanded {
    transition: 0.2s all 0s;
    transform: rotate(-180deg);
  }
}
</style>
