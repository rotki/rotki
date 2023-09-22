<script setup lang="ts">
defineProps<{
  icon: string;
}>();
const emit = defineEmits<{
  (e: 'confirm'): void;
  (e: 'cancel'): void;
}>();
const { t } = useI18n();
const css = useCssModule();
const slots = useSlots();
</script>

<template>
  <VAlert
    class="animate mt-8"
    text
    prominent
    outlined
    type="warning"
    :icon="icon"
  >
    <div class="text-h6">
      <slot name="title" />
    </div>
    <div class="mt-2" :class="css.body">
      <div>
        <slot />
      </div>
    </div>

    <VRow justify="end" class="mt-2">
      <VCol cols="auto" class="shrink">
        <RuiButton color="error" @click="emit('cancel')">
          <slot v-if="slots.cancel" name="cancel" />
          <span v-else> {{ t('common.actions.no') }} </span>
        </RuiButton>
      </VCol>
      <VCol cols="auto" class="shrink">
        <RuiButton color="success" @click="emit('confirm')">
          <slot v-if="slots.confirm" name="confirm" />
          <span v-else> {{ t('common.actions.yes') }} </span>
        </RuiButton>
      </VCol>
    </VRow>
  </VAlert>
</template>

<style module lang="scss">
.body {
  margin-top: 5px;
  margin-bottom: 8px;
}
</style>
