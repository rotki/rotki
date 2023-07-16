<script setup lang="ts">
defineProps({
  disabled: { required: false, type: Boolean, default: false }
});

const emit = defineEmits(['ignore']);

const ignore = (ignore: boolean) => emit('ignore', ignore);

const { t } = useI18n();
</script>

<template>
  <VRow no-gutters>
    <VCol cols="auto">
      <VTooltip top open-delay="400">
        <template #activator="{ on, attrs }">
          <VBtn
            text
            v-bind="attrs"
            :disabled="disabled"
            outlined
            v-on="on"
            @click="ignore(true)"
          >
            {{ t('ignore_buttons.ignore') }}
          </VBtn>
        </template>
        <span>{{ t('ignore_buttons.ignore_tooltip') }}</span>
      </VTooltip>
    </VCol>
    <VCol cols="auto">
      <VTooltip top open-delay="400">
        <template #activator="{ on, attrs }">
          <VBtn
            v-bind="attrs"
            text
            :disabled="disabled"
            outlined
            class="ms-2"
            v-on="on"
            @click="ignore(false)"
          >
            {{ t('ignore_buttons.unignore') }}
          </VBtn>
        </template>
        <span>{{ t('ignore_buttons.unignore_tooltip') }}</span>
      </VTooltip>
    </VCol>
  </VRow>
</template>
