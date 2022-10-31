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
    <v-col cols="auto">{{ t('pagination.of', { length }) }}</v-col>
    <v-col cols="auto">
      <v-btn icon :disabled="value === length" @click="nextPage">
        <v-icon>mdi-chevron-right</v-icon>
      </v-btn>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { useTheme } from '@/composables/common';

const props = defineProps({
  value: {
    required: true,
    type: Number
  },
  length: {
    required: true,
    type: Number
  }
});

const emit = defineEmits(['input']);
const { length, value } = toRefs(props);
const items = computed(() => {
  const items: number[] = [];

  for (let i = 1; i <= get(length); i++) {
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
  if (get(value) < get(length)) {
    changePage(get(value) + 1);
  }
};

const previousPage = () => {
  if (get(value) > 1) {
    changePage(get(value) - 1);
  }
};

const { dark } = useTheme();
const { t } = useI18n();
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
