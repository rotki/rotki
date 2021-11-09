<template>
  <v-row align="center">
    <v-col cols="auto">
      <v-btn icon :disabled="value === 1" @click="previousPage">
        <v-icon>mdi-chevron-left</v-icon>
      </v-btn>
    </v-col>
    <v-col cols="auto">
      <div
        :class="{
          [$style.pages]: true,
          [$style.light]: !dark,
          [$style.dark]: dark
        }"
      >
        <v-autocomplete
          :items="items"
          :value="value"
          single-line
          hide-details
          dense
          hide-no-data
          outlined
          @change="newPage"
        />
      </div>
    </v-col>
    <v-col cols="auto">{{ $t('pagination.of', { length }) }}</v-col>
    <v-col cols="auto">
      <v-btn icon :disabled="value === length" @click="nextPage">
        <v-icon>mdi-chevron-right</v-icon>
      </v-btn>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { setupThemeCheck } from '@/composables/common';

export default defineComponent({
  name: 'Pagination',
  props: {
    value: {
      required: true,
      type: Number
    },
    length: {
      required: true,
      type: Number
    }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { length, value } = toRefs(props);
    const items = computed(() => {
      const items: number[] = [];

      for (let i = 1; i <= length.value; i++) {
        items.push(i);
      }
      return items;
    });

    const changePage = (page: number) => {
      emit('input', page);
    };

    const newPage = (data?: any) => {
      if (!data) {
        return;
      }

      const page = parseInt(data);
      if (isNaN(page)) {
        return;
      }
      changePage(page);
    };

    const nextPage = () => {
      if (value.value < length.value) {
        changePage(value.value + 1);
      }
    };

    const previousPage = () => {
      if (value.value > 1) {
        changePage(value.value - 1);
      }
    };

    const { dark } = setupThemeCheck();

    return {
      items,
      nextPage,
      previousPage,
      newPage,
      dark
    };
  }
});
</script>

<style module lang="scss">
.pages {
  max-width: 80px;

  :global {
    .v-autocomplete {
      &.v-select {
        &.v-input {
          &--is-focused {
            input {
              min-width: 28px !important;
            }
          }
        }
      }
    }
  }
}

.dark {
  background-color: var(--v-dark-base);
}

.light {
  background-color: white;
}
</style>
