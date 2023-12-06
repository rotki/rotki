<script setup lang="ts">
const props = defineProps<{
  value: number;
  length: number;
}>();

const emit = defineEmits<{ (e: 'input', value: number): void }>();
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

const { t } = useI18n();

const css = useCssModule();
</script>

<template>
  <div class="flex items-center gap-4">
    <RuiButton
      variant="text"
      class="!p-2"
      icon
      :disabled="value === 1"
      @click="previousPage()"
    >
      <RuiIcon name="arrow-left-s-line" />
    </RuiButton>
    <div :class="[css.pages, 'bg-white dark:bg-rui-grey-900']">
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
    <div>{{ t('pagination.of', { length }) }}</div>
    <RuiButton
      variant="text"
      icon
      class="!p-2"
      :disabled="value === length"
      @click="nextPage()"
    >
      <RuiIcon name="arrow-right-s-line" />
    </RuiButton>
  </div>
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
</style>
