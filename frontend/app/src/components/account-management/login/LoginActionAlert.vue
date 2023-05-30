<script setup lang="ts">
const { t } = useI18n();
const css = useCssModule();
const slots = useSlots();

defineProps<{
  icon: string;
}>();

const emit = defineEmits<{
  (e: 'confirm'): void;
  (e: 'cancel'): void;
}>();
</script>

<template>
  <v-alert
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

    <v-row justify="end" class="mt-2">
      <v-col cols="auto" class="shrink">
        <v-btn color="error" depressed @click="emit('cancel')">
          <slot v-if="slots.cancel" name="cancel" />
          <span v-else> {{ t('common.actions.no') }} </span>
        </v-btn>
      </v-col>
      <v-col cols="auto" class="shrink">
        <v-btn color="success" depressed @click="emit('confirm')">
          <slot v-if="slots.confirm" name="confirm" />
          <span v-else> {{ t('common.actions.yes') }} </span>
        </v-btn>
      </v-col>
    </v-row>
  </v-alert>
</template>

<style module lang="scss">
.body {
  margin-top: 5px;
  margin-bottom: 8px;
}
</style>
