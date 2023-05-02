<script setup lang="ts">
withDefaults(
  defineProps<{
    disabled?: boolean;
    editDisabled?: boolean;
    editTooltip?: string;
    noEdit?: boolean;
    deleteDisabled?: boolean;
    deleteTooltip?: string;
    noDelete?: false;
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
    <v-tooltip v-if="!noEdit" top>
      <template #activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          icon
          :disabled="disabled || editDisabled"
          class="mx-1 actions__edit"
          data-cy="row-edit"
          v-on="on"
          @click="editClick()"
        >
          <v-icon small> mdi-pencil-outline </v-icon>
        </v-btn>
      </template>
      <span>{{ editTooltip }}</span>
    </v-tooltip>
    <v-tooltip v-if="!noDelete" top>
      <template #activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          icon
          :disabled="disabled || deleteDisabled"
          class="mx-1 actions__delete"
          data-cy="row-delete"
          v-on="on"
          @click="deleteClick()"
        >
          <v-icon small> mdi-delete-outline </v-icon>
        </v-btn>
      </template>
      <span>{{ deleteTooltip }}</span>
    </v-tooltip>
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
