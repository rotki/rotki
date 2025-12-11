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

const editClick = () => emit('edit-click');
const deleteClick = () => emit('delete-click');

const tooltipProps = {
  openDelay: 400,
  popper: { offsetDistance: 0, placement: 'top' as const },
};

const justify = computed(() => {
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
    <RuiTooltip
      v-if="!noEdit"
      v-bind="tooltipProps"
      :disabled="!editTooltip"
      tooltip-class="max-w-[20rem]"
    >
      <template #activator>
        <RuiButton
          :disabled="disabled || editDisabled"
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
      </template>
      {{ editTooltip }}
    </RuiTooltip>
    <RuiTooltip
      v-if="!noDelete"
      v-bind="tooltipProps"
      :disabled="!deleteTooltip"
      tooltip-class="max-w-[20rem]"
    >
      <template #activator>
        <RuiButton
          :disabled="disabled || deleteDisabled"
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
      </template>
      {{ deleteTooltip }}
    </RuiTooltip>
    <slot />
  </div>
</template>
