<script setup lang="ts">
import type { PullEventPayload } from '@/types/history/events';

const show = defineModel<boolean>('show', { required: true });

const props = defineProps<{
  payload: PullEventPayload | undefined;
}>();

const emit = defineEmits<{
  confirm: [event: { payload: PullEventPayload; deleteCustom: boolean }];
}>();

const deleteCustom = ref(false);

const { t } = useI18n({ useScope: 'global' });

function confirmRedecode(): void {
  const payload = props.payload;
  if (payload) {
    emit('confirm', {
      deleteCustom: get(deleteCustom),
      payload,
    });
  }
  set(show, false);
  set(deleteCustom, false);
}
</script>

<template>
  <RuiDialog
    v-model="show"
    :max-width="500"
  >
    <RuiCard class="[&>div:first-child]:pb-0">
      <template #header>
        {{ t('transactions.actions.redecode_events') }}
      </template>
      <div class="mb-2">
        {{ t('transactions.events.confirmation.reset.message') }}
      </div>
      <RuiRadioGroup
        v-model="deleteCustom"
        color="primary"
      >
        <RuiRadio :value="false">
          {{ t('transactions.events.confirmation.reset.options.keep_custom_events') }}
        </RuiRadio>
        <RuiRadio :value="true">
          {{ t('transactions.events.confirmation.reset.options.remove_custom_events') }}
        </RuiRadio>
      </RuiRadioGroup>
      <template #footer>
        <div class="grow" />
        <RuiButton
          color="primary"
          @click="confirmRedecode()"
        >
          {{ t('common.actions.proceed') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
