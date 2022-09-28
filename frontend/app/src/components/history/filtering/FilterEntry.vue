<template>
  <div>
    <v-btn
      text
      color="primary"
      :class="css.button"
      class="text-none text-body-1"
      @click="click(matcher.key)"
    >
      <span class="text-start" :class="css.wrapper">
        <span class="font-weight-medium"> {{ matcher.key }}: </span>
        <span
          class="ms-2 text--secondary font-weight-regular"
          :class="css.description"
        >
          {{ matcher.description }}
        </span>
      </span>
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { SearchMatcher } from '@/types/filtering';

defineProps({
  matcher: {
    required: true,
    type: Object as PropType<SearchMatcher<any>>
  }
});

const emit = defineEmits<{ (e: 'click', key: string): void }>();
const css = useCssModule();

const click = (key: string) => {
  emit('click', key);
};
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
