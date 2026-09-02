<script setup lang="ts">
import PremiumLock from '@/modules/premium/PremiumLock.vue';
import AppImage from '@/modules/shell/components/AppImage.vue';
import BigDialog, { type BigDialogAction } from '@/modules/shell/components/dialogs/BigDialog.vue';

export interface FeatureGate {
  allowed: boolean;
  message: string;
}

export interface ServiceKeyAction {
  disabled?: boolean;
  hidden?: boolean;
  primary?: string;
  addText?: string;
  editText?: string;
}

const {
  action,
  name,
  title,
  subtitle = '',
  imageSrc,
  featureGate,
  roundedIcon = false,
  keySet = false,
} = defineProps<{
  name?: string;
  title: string;
  subtitle?: string;
  imageSrc: string;
  featureGate?: FeatureGate;
  roundedIcon?: boolean;
  keySet?: boolean;
  action?: ServiceKeyAction;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

defineSlots<{
  'default': () => any;
  'left-buttons': () => any;
  'banner': () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const openDialog = ref<boolean>(false);

const featureBlocked = computed<boolean>(() => !!featureGate && !featureGate.allowed);

function setOpen(value: boolean): void {
  set(openDialog, value);
}

const route = useRoute();
const router = useRouter();

watch(route, async (route) => {
  if (!name)
    return;

  const { query } = route;
  if (!query) {
    return;
  }
  const { service, ...restQuery } = query;

  if (service === name) {
    nextTick(() => {
      setOpen(true);
    });
    await router.replace({ query: restQuery });
  }
}, { immediate: true });

const actionDisabled = computed<boolean>(() => action?.disabled ?? false);

const actionHidden = computed<boolean>(() => action?.hidden ?? false);

const addButtonText = computed<string>(() => action?.addText || t('external_services.actions.enter_api_key'));

const editButtonText = computed<string>(() => action?.editText || t('external_services.actions.replace_key'));

const primaryActionText = computed<string>(() => action?.primary || (keySet
  ? t('external_services.actions.replace_key')
  : t('external_services.actions.save_key')));

const dialogAction = computed<BigDialogAction>(() => ({
  disabled: get(actionDisabled),
  hidden: get(actionHidden),
  primary: get(primaryActionText),
  secondary: t('common.actions.close'),
}));

defineExpose({
  openDialog,
  setOpen,
});
</script>

<template>
  <RuiCard
    no-padding
    class="h-full"
    :class="{ '!border-rui-success/50 bg-rui-success/5 dark:bg-rui-success/5': keySet }"
    :class-names="{ content: 'h-full flex flex-col' }"
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
      <div
        v-if="$slots.banner"
        class="px-6 pb-2"
      >
        <slot name="banner" />
      </div>
    </div>
    <div
      v-if="featureBlocked"
      class="py-2.5 px-6 -ml-4 flex items-center gap-2 text-body-2 border-t border-default text-rui-text-secondary"
    >
      <PremiumLock />
      {{ featureGate?.message }}
    </div>
    <div
      v-else
      class="px-6 py-4 border-t border-default"
      :class="{ '!border-rui-success/20': keySet }"
    >
      <RuiButton
        variant="outlined"
        color="primary"
        @click="setOpen(true)"
      >
        {{
          keySet
            ? editButtonText
            : addButtonText
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
      :action="dialogAction"
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
