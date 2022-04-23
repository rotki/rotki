<template>
  <div>
    <v-btn
      text
      color="primary"
      :class="$style.button"
      class="text-none text-body-1"
      @click="click(matcher.key)"
    >
      <span class="text-start" :class="$style.wrapper">
        <span class="font-weight-medium"> {{ matcher.key }}: </span>
        <span
          class="ms-2 text--secondary font-weight-regular"
          :class="$style.description"
        >
          {{ matcher.description }}
        </span>
      </span>
    </v-btn>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { SearchMatcher } from '@/components/history/filtering/types';

export default defineComponent({
  name: 'FilterEntry',
  props: {
    matcher: {
      required: true,
      type: Object as PropType<SearchMatcher<any>>
    }
  },
  emits: ['click'],
  setup(props, { emit }) {
    const click = (key: string) => {
      emit('click', key);
    };
    return {
      click
    };
  }
});
</script>

<style module>
.button {
  width: 100%;
  height: auto !important;
  padding: 0.5rem !important;
  display: block;
}

.wrapper {
  width: 100%;
  max-width: 100%;
  display: flex;
}

.description {
  white-space: normal;
}
</style>
