<script setup lang="ts">
import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import AccountValueEditor from '@/modules/core/table/pill/AccountValueEditor.vue';
import AssetValueEditor from '@/modules/core/table/pill/AssetValueEditor.vue';
import { resolveEditor } from '@/modules/core/table/pill/core/field-adapter';
import DateValueEditor from '@/modules/core/table/pill/DateValueEditor.vue';
import EnumValueEditor from '@/modules/core/table/pill/EnumValueEditor.vue';
import RangeValueEditor from '@/modules/core/table/pill/RangeValueEditor.vue';
import TextValueEditor from '@/modules/core/table/pill/TextValueEditor.vue';

const { field, filter } = defineProps<{
  field: FieldDef;
  filter: ActiveFilter;
}>();

const emit = defineEmits<{
  update: [filter: ActiveFilter];
  /**
   * The editor is done (enter committed a range, Escape dismissed a list), so the bar can close
   * its popover. Every editor emits it: leaning on the menu's own dismissal only worked while its
   * content held focus, which made Escape mean different things in different editors.
   */
  close: [];
  /**
   * Only the date editor raises this: its picker teleports a calendar outside the editor's popover,
   * so the bar has to hold that popover open while the calendar is up or a click in it reads as a
   * click away.
   */
  persist: [value: boolean];
}>();

const editor = computed(() => resolveEditor(field));
</script>

<template>
  <EnumValueEditor
    v-if="editor === 'enum'"
    :field="field"
    :filter="filter"
    @update="emit('update', $event)"
    @close="emit('close')"
  />
  <RangeValueEditor
    v-else-if="editor === 'range'"
    :field="field"
    :filter="filter"
    @update="emit('update', $event)"
    @close="emit('close')"
  />
  <DateValueEditor
    v-else-if="editor === 'date'"
    :field="field"
    :filter="filter"
    @update="emit('update', $event)"
    @close="emit('close')"
    @persist="emit('persist', $event)"
  />
  <AccountValueEditor
    v-else-if="editor === 'account'"
    :field="field"
    :filter="filter"
    @update="emit('update', $event)"
    @close="emit('close')"
  />
  <AssetValueEditor
    v-else-if="editor === 'asset'"
    :field="field"
    :filter="filter"
    @update="emit('update', $event)"
    @close="emit('close')"
  />
  <TextValueEditor
    v-else-if="editor === 'text'"
    :field="field"
    :filter="filter"
    @update="emit('update', $event)"
    @close="emit('close')"
  />
</template>
