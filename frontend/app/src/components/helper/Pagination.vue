<script setup lang="ts">
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

  const page = Number.parseInt(data);
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

<template>
  <VRow align="center">
    <VCol cols="auto">
      <RuiButton
        icon
        variant="text"
        :disabled="value === 1"
        @click="previousPage()"
      >
        <VIcon>mdi-chevron-left</VIcon>
      </RuiButton>
    </VCol>
    <VCol cols="auto">
      <div
        :class="{
          [$style.pages]: true,
          [$style.light]: !dark,
          [$style.dark]: dark
        }"
      >
        <VAutocomplete
          :items="items"
          :value="value"
          single-line
          hide-details
          dense
          hide-no-data
          outlined
          @change="newPage($event)"
        />
      </div>
    </VCol>
    <VCol cols="auto">{{ t('pagination.of', { length }) }}</VCol>
    <VCol cols="auto">
      <RuiButton
        icon
        variant="text"
        :disabled="value === length"
        @click="nextPage()"
      >
        <VIcon>mdi-chevron-right</VIcon>
      </RuiButton>
    </VCol>
  </VRow>
</template>

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
