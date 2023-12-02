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
    disabled: false,
    editDisabled: false,
    editTooltip: '',
    noEdit: false,
    deleteDisabled: false,
    deleteTooltip: '',
    noDelete: false,
    align: 'start'
  }
);

const emit = defineEmits<{
  (e: 'edit-click'): void;
  (e: 'delete-click'): void;
}>();

const editClick = () => emit('edit-click');
const deleteClick = () => emit('delete-click');

const tooltipProps = {
  popper: { placement: 'top', offsetDistance: 0 },
  openDelay: '400'
};

const justify = computed(() => {
  const justify = {
    start: 'justify-start',
    center: 'justify-center',
    end: 'justify-end'
  } as const;
  return justify[props.align];
});
</script>

<template>
  <div class="flex flex-row flex-nowrap items-center gap-1" :class="justify">
    <RuiTooltip v-if="!noEdit" v-bind="tooltipProps">
      <template #activator>
        <RuiButton
          :disabled="disabled || editDisabled"
          variant="text"
          data-cy="row-edit"
          icon
          @click="editClick()"
        >
          <RuiIcon size="16" name="pencil-line" />
        </RuiButton>
      </template>
      {{ editTooltip }}
    </RuiTooltip>
    <RuiTooltip v-if="!noDelete" v-bind="tooltipProps">
      <template #activator>
        <RuiButton
          :disabled="disabled || deleteDisabled"
          variant="text"
          data-cy="row-delete"
          icon
          @click="deleteClick()"
        >
          <RuiIcon size="16" name="delete-bin-line" />
        </RuiButton>
      </template>
      {{ deleteTooltip }}
    </RuiTooltip>
    <slot />
  </div>
</template>
