<script setup lang="ts">
import { type PropType } from 'vue';

const props = defineProps({
  sortBy: {
    required: true,
    type: String
  },
  sortDesc: {
    required: true,
    type: Boolean
  },
  sortProperties: {
    required: true,
    type: Array as PropType<{ text: string; value: string }[]>
  }
});

const emit = defineEmits(['update:sort-by', 'update:sort-desc']);
const { sortDesc: sortDescending } = toRefs(props);
const updateSortBy = (value: string) => {
  emit('update:sort-by', value);
};
const updateSortDesc = () => {
  emit('update:sort-desc', !get(sortDescending));
};
const { dark } = useTheme();

const { t } = useI18n();
</script>

<template>
  <div :class="$style.container">
    <div>
      <VTooltip open-delay="400" top>
        <template #activator="{ on, attrs }">
          <RuiButton
            icon
            variant="text"
            v-bind="attrs"
            color="primary"
            @click="updateSortDesc()"
            v-on="on"
          >
            <VIcon v-if="sortDescending">mdi-sort-descending</VIcon>
            <VIcon v-else>mdi-sort-ascending</VIcon>
          </RuiButton>
        </template>
        <span v-if="sortDescending">
          {{ t('sorting_selector.desc.sort_asc_tooltip') }}
        </span>
        <span v-else>{{ t('sorting_selector.desc.sort_desc_tooltip') }}</span>
      </VTooltip>
    </div>
    <div
      :class="{
        [$style.selector]: true,
        [$style.light]: !dark,
        [$style.dark]: dark
      }"
    >
      <VSelect
        :value="sortBy"
        hide-details
        single-line
        dense
        outlined
        :items="sortProperties"
        @input="updateSortBy($event)"
      />
    </div>
  </div>
</template>

<style module lang="scss">
.container {
  display: flex;
  flex-direction: row;
}

.selector {
  flex: 1;
  margin-left: 8px;
}

.dark {
  background-color: var(--v-dark-base);
}

.light {
  background-color: white;
}
</style>
