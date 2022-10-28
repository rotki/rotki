<template>
  <div :class="$style.container">
    <div>
      <v-tooltip open-delay="400" top>
        <template #activator="{ on, attrs }">
          <v-btn
            icon
            v-bind="attrs"
            color="primary"
            @click="updateSortDesc"
            v-on="on"
          >
            <v-icon v-if="sortDesc">mdi-sort-descending</v-icon>
            <v-icon v-else>mdi-sort-ascending</v-icon>
          </v-btn>
        </template>
        <span v-if="sortDesc">
          {{ t('sorting_selector.desc.sort_asc_tooltip') }}
        </span>
        <span v-else>{{ t('sorting_selector.desc.sort_desc_tooltip') }}</span>
      </v-tooltip>
    </div>
    <div
      :class="{
        [$style.selector]: true,
        [$style.light]: !dark,
        [$style.dark]: dark
      }"
    >
      <v-select
        :value="sortBy"
        hide-details
        single-line
        dense
        outlined
        :items="sortProperties"
        @input="updateSortBy"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { useTheme } from '@/composables/common';

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
const { sortDesc } = toRefs(props);
const updateSortBy = (value: string) => {
  emit('update:sort-by', value);
};
const updateSortDesc = () => {
  emit('update:sort-desc', !get(sortDesc));
};
const { dark } = useTheme();

const { t } = useI18n();
</script>

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
