<script setup lang="ts">
withDefaults(
  defineProps<{
    tooltip?: string;
    loading?: boolean;
    disabled?: boolean;
  }>(),
  {
    tooltip: '',
    loading: false,
    disabled: false
  }
);

const emit = defineEmits<{ (e: 'reset'): void }>();

const menu = ref<boolean>(false);

const reset = () => {
  set(menu, false);
  emit('reset');
};

const { t } = useI18n();
</script>

<template>
  <VMenu
    v-model="menu"
    :nudge-width="150"
    offset-x
    :close-on-content-click="false"
  >
    <template #activator="{ on: menuListeners, attrs }">
      <VTooltip top>
        <template #activator="{ on: tooltipListeners }">
          <VBtn
            v-bind="attrs"
            icon
            fab
            small
            depressed
            :disabled="loading"
            v-on="{ ...menuListeners, ...tooltipListeners }"
          >
            <VIcon color="primary">mdi-database-refresh</VIcon>
          </VBtn>
        </template>
        {{ tooltip }}
      </VTooltip>
    </template>
    <VCard max-width="280px">
      <VCardTitle>{{ t('common.actions.confirm') }}</VCardTitle>
      <VCardText>
        <slot>{{ t('confirmable_reset.confirm.message') }}</slot>
      </VCardText>
      <VCardActions>
        <VSpacer />
        <VBtn text @click="menu = false">
          {{ t('common.actions.cancel') }}
        </VBtn>
        <VBtn color="primary" text :disabled="disabled" @click="reset()">
          {{ t('common.actions.confirm') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VMenu>
</template>
