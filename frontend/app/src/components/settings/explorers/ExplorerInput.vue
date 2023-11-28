<script setup lang="ts">
import { useListeners } from 'vue';

const props = defineProps<{
  value: string;
}>();

const emit = defineEmits<{
  (e: 'input', value: string): void;
  (e: 'save-data', value?: string): void;
}>();

const { value } = toRefs(props);

const model = computed({
  get() {
    return get(value);
  },
  set(value) {
    emit('input', value);
  }
});

const attrs = useAttrs();
const listeners = useListeners();

const isValid = (entry: string | null): boolean =>
  !entry ? false : entry.length > 0;

const saveData = (value?: string) => {
  emit('save-data', value);
};
</script>

<template>
  <div class="flex items-start gap-4">
    <VTextField
      v-model="model"
      class="flex-1"
      outlined
      clearable
      persistent-hint
      v-bind="attrs"
      v-on="listeners"
      @click:clear="saveData()"
    >
      <template #append-outer />
    </VTextField>
    <RuiButton
      variant="text"
      class="mt-1"
      icon
      :disabled="!isValid(value)"
      @click="saveData(value)"
    >
      <RuiIcon name="save-line" />
    </RuiButton>
  </div>
</template>
