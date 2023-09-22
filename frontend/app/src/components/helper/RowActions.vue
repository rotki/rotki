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
</script>

<template>
  <div :class="css.actions">
    <VTooltip v-if="!noEdit" top>
      <template #activator="{ on, attrs }">
        <RuiButton
          v-bind="attrs"
          icon
          variant="text"
          :disabled="disabled || editDisabled"
          class="mx-1 actions__edit"
          data-cy="row-edit"
          v-on="on"
          @click="editClick()"
        >
          <VIcon small> mdi-pencil-outline </VIcon>
        </RuiButton>
      </template>
      <span>{{ editTooltip }}</span>
    </VTooltip>
    <VTooltip v-if="!noDelete" top>
      <template #activator="{ on, attrs }">
        <RuiButton
          v-bind="attrs"
          icon
          variant="text"
          :disabled="disabled || deleteDisabled"
          class="mx-1 actions__delete"
          data-cy="row-delete"
          v-on="on"
          @click="deleteClick()"
        >
          <VIcon small> mdi-delete-outline </VIcon>
        </RuiButton>
      </template>
      <span>{{ deleteTooltip }}</span>
    </VTooltip>
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
