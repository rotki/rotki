<script setup lang="ts">
defineProps({
  disabled: { required: false, type: Boolean, default: false }
});

const emit = defineEmits(['ignore']);

const ignore = (ignore: boolean) => emit('ignore', ignore);

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-row items-center">
    <RuiTooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <RuiButton
          v-bind="attrs"
          :disabled="disabled"
          variant="outlined"
          v-on="on"
          @click="ignore(true)"
        >
          {{ t('ignore_buttons.ignore') }}
        </RuiButton>
      </template>
      <span>{{ t('ignore_buttons.ignore_tooltip') }}</span>
    </RuiTooltip>
    <RuiTooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <RuiButton
          v-bind="attrs"
          :disabled="disabled"
          variant="outlined"
          class="ms-2"
          v-on="on"
          @click="ignore(false)"
        >
          {{ t('ignore_buttons.unignore') }}
        </RuiButton>
      </template>
      <span>{{ t('ignore_buttons.unignore_tooltip') }}</span>
    </RuiTooltip>
  </div>
</template>
