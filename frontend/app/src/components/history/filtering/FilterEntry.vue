<template>
  <div>
    <v-btn
      text
      color="primary"
      :class="$style.fullwidth"
      class="text-none text-body-1"
      @click="click(matcher.key)"
    >
      <span class="text-start" :class="$style.fullwidth">
        <span class="font-weight-medium"> {{ matcher.key }}: </span>
        <span class="ms-2 text--secondary font-weight-regular">
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
.fullwidth {
  width: 100%;
}
</style>
