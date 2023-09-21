<script setup lang="ts">
import { type SearchMatcher } from '@/types/filtering';

defineProps<{
  matcher: SearchMatcher<any>;
  active: boolean;
}>();

const emit = defineEmits<{ (e: 'click', matcher: SearchMatcher<any>): void }>();
const css = useCssModule();

const click = (matcher: SearchMatcher<any>) => {
  emit('click', matcher);
};

const { dark } = useTheme();
</script>

<template>
  <div>
    <VBtn
      text
      class="text-none text-body-1"
      block
      :class="[
        {
          [css.button]: true,
          [css.selected]: active
        },
        dark && active ? 'black--text' : 'text--secondary'
      ]"
      @click="click(matcher)"
    >
      <span class="text-start" :class="css.wrapper">
        <span class="font-medium primary--text"> {{ matcher.key }}: </span>
        <span class="ms-2 font-weight-regular" :class="css.description">
          {{ matcher.description }}
        </span>
      </span>
    </VBtn>
  </div>
</template>

<style module lang="scss">
.button {
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

.selected {
  background-color: var(--v-primary-lighten4);
}
</style>
