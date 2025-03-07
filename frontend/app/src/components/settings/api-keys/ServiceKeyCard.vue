<script setup lang="ts">
import { usePremium } from '@/composables/premium';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import AppImage from '@/components/common/AppImage.vue';

withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    imageSrc: string;
    needPremium?: boolean;
    roundedIcon?: boolean;
    keySet?: boolean;
    hideAction?: boolean;
    primaryAction?: string;
    actionDisabled?: boolean;
  }>(),
  {
    actionDisabled: false,
    hideAction: false,
    keySet: false,
    needPremium: false,
    primaryAction: '',
    roundedIcon: false,
    subtitle: '',
  },
);

const emit = defineEmits<{
  (e: 'confirm'): void;
}>();

defineSlots<{
  'default': () => any;
  'left-buttons': () => any;
}>();

const { t } = useI18n();

const openDialog = ref<boolean>(false);

const premium = usePremium();

function setOpen(value: boolean) {
  set(openDialog, value);
}

defineExpose({
  setOpen,
});
</script>

<template>
  <RuiCard
    no-padding
    class="h-full"
    content-class="h-full flex flex-col"
  >
    <div class="grow">
      <div class="px-6 pt-6">
        <AppImage
          :src="imageSrc"
          class="size-10"
          :class="{ 'rounded-full overflow-hidden': roundedIcon }"
        />
      </div>
      <RuiCardHeader class="!px-6">
        <template #header>
          {{ title }}
        </template>
        <template #subheader>
          {{ subtitle }}
        </template>
      </RuiCardHeader>
    </div>
    <div
      v-if="needPremium && !premium"
      class="py-2.5 px-6 -ml-4 flex items-center gap-2 text-body-2 border-t border-default text-rui-text-secondary"
    >
      <PremiumLock />
      {{ t('external_services.need_premium') }}
    </div>
    <div
      v-else
      class="px-6 py-4 border-t border-default"
    >
      <RuiButton
        variant="outlined"
        color="primary"
        @click="setOpen(true)"
      >
        {{
          keySet
            ? t('external_services.replace_key')
            : t('external_services.enter_api_key')
        }}
        <template #append>
          <RuiIcon
            name="lu-arrow-right"
            size="16"
          />
        </template>
      </RuiButton>
    </div>
    <BigDialog
      :display="openDialog"
      :title="title"
      :subtitle="subtitle"
      :action-hidden="hideAction"
      :primary-action="primaryAction"
      :action-disabled="actionDisabled"
      :secondary-action="t('common.actions.close')"
      @cancel="setOpen(false)"
      @confirm="emit('confirm')"
    >
      <template #left-buttons>
        <slot name="left-buttons" />
      </template>
      <slot />
    </BigDialog>
  </RuiCard>
</template>
