<script setup lang="ts">
import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import ValueSelectList from '@/modules/core/table/pill/ValueSelectList.vue';
import { useAccountFilterOptions } from '@/modules/history/use-account-filter-options';
import { useScramble } from '@/modules/settings/use-scramble';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';

const { field, filter } = defineProps<{
  field: FieldDef;
  filter: ActiveFilter;
}>();

const emit = defineEmits<{
  update: [filter: ActiveFilter];
  /** Escape in the list: the editor is done, so the bar can close its popover. */
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { scrambleAddress } = useScramble();
const { options } = useAccountFilterOptions();

const selected = computed<string[]>({
  get() {
    return filter.values;
  },
  set(values: string[]) {
    emit('update', { ...filter, values });
  },
});
</script>

<template>
  <ValueSelectList
    v-model="selected"
    :options="options"
    :multiple="field.multiple"
    :search-placeholder="t('common.actions.search')"
    :empty-text="t('data_table.no_data')"
    @close="emit('close')"
  >
    <template #icon="{ value }">
      <EnsAvatar
        :address="scrambleAddress(value)"
        avatar
        size="20px"
        class="shrink-0"
      />
    </template>
  </ValueSelectList>
</template>
