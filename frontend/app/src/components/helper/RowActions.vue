<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    editDisabled?: boolean;
    editTooltip?: string;
    noEdit?: boolean;
    deleteDisabled?: boolean;
    deleteTooltip?: string;
    noDelete?: boolean;
    align?: 'start' | 'center' | 'end';
  }>(),
  {
    align: 'start',
    deleteDisabled: false,
    deleteTooltip: '',
    disabled: false,
    editDisabled: false,
    editTooltip: '',
    noDelete: false,
    noEdit: false,
  },
);

const emit = defineEmits<{
  'edit-click': [];
  'delete-click': [];
}>();

const editClick = (): void => emit('edit-click');
const deleteClick = (): void => emit('delete-click');

const justify = computed<string>(() => {
  const justify = {
    center: 'justify-center',
    end: 'justify-end',
    start: 'justify-start',
  } as const;
  return justify[props.align];
});
</script>

<template>
  <div
    class="flex flex-row flex-nowrap items-center gap-1"
    :class="justify"
  >
    <RuiButton
      v-if="!noEdit"
      :disabled="disabled || editDisabled"
      :title="editTooltip || undefined"
      variant="text"
      data-cy="row-edit"
      icon
      @click="editClick()"
    >
      <RuiIcon
        size="16"
        name="lu-pencil"
      />
    </RuiButton>
    <RuiButton
      v-if="!noDelete"
      :disabled="disabled || deleteDisabled"
      :title="deleteTooltip || undefined"
      variant="text"
      data-cy="row-delete"
      icon
      @click="deleteClick()"
    >
      <RuiIcon
        size="16"
        name="lu-trash-2"
      />
    </RuiButton>
    <slot />
  </div>
</template>
