<script setup lang="ts">
withDefaults(
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

const css = useCssModule();

const tooltipProps = {
  popper: { placement: 'top', offsetDistance: 0 },
  openDelay: '400'
};
</script>

<template>
  <div :class="css.actions">
    <RuiTooltip v-if="!noEdit" v-bind="tooltipProps">
      <template #activator>
        <RuiButton
          :disabled="disabled || editDisabled"
          variant="text"
          class="mx-1"
          data-cy="row-edit"
          icon
          @click="editClick()"
        >
          <RuiIcon size="16" name="pencil-line" />
        </RuiButton>
      </template>
      <span>{{ editTooltip }}</span>
    </RuiTooltip>
    <RuiTooltip v-if="!noDelete" v-bind="tooltipProps">
      <template #activator>
        <RuiButton
          :disabled="disabled || deleteDisabled"
          variant="text"
          class="mx-1"
          data-cy="row-delete"
          icon
          @click="deleteClick()"
        >
          <RuiIcon size="16" name="delete-bin-line" />
        </RuiButton>
      </template>
      <span>{{ deleteTooltip }}</span>
    </RuiTooltip>
    <slot />
  </div>
</template>

<style module lang="scss">
.actions {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: v-bind(align);
}
</style>
