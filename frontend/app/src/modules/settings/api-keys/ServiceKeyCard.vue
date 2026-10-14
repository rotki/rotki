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
  /** What the status chip says once the service is set up; a key card's default is "Key set". */
  statusText?: string;
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
  /** Set for a service that needs a premium plan; the card says so whether or not the plan allows it. */
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
  <section class="flex h-full flex-col rounded-rui-card border border-rui-divider bg-rui-surface">
    <div class="flex grow flex-col gap-3 p-4">
      <div class="flex items-center gap-3 min-w-0">
        <AppImage
          :src="imageSrc"
          class="size-9 shrink-0"
          :class="{ 'rounded-full overflow-hidden': roundedIcon }"
        />
        <h3 class="m-0 grow min-w-0 truncate text-base font-semibold text-rui-text">
          {{ title }}
        </h3>
        <div class="flex shrink-0 items-center gap-1.5">
          <RuiTooltip
            v-if="featureGate"
            :open-delay="400"
          >
            <template #activator>
              <span
                class="flex size-6 items-center justify-center rounded-full bg-rui-primary/10 text-rui-primary"
                data-testid="service-key-premium"
              >
                <RuiIcon
                  name="lu-crown"
                  size="14"
                />
              </span>
            </template>
            {{ t('external_services.status.premium') }}
          </RuiTooltip>
          <RuiChip
            v-if="keySet"
            size="sm"
            variant="tonal"
            color="success"
            data-testid="service-key-status"
          >
            {{ action?.statusText || t('external_services.status.key_set') }}
          </RuiChip>
        </div>
      </div>
      <p
        class="m-0 text-sm text-rui-text-secondary line-clamp-3"
        :title="subtitle"
      >
        {{ subtitle }}
      </p>
      <div v-if="$slots.banner">
        <slot name="banner" />
      </div>
    </div>
    <div
      v-if="featureBlocked"
      class="flex items-center gap-2 border-t border-rui-divider px-4 py-2.5 text-sm text-rui-text-secondary"
    >
      <PremiumLock />
      {{ featureGate?.message }}
    </div>
    <div
      v-else
      class="border-t border-rui-divider px-4 py-3"
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
      :layout="{ autoHeight: true, divide: true, maxWidth: '600px' }"
      @cancel="setOpen(false)"
      @confirm="emit('confirm')"
    >
      <template #header>
        <div class="flex items-center gap-3 mb-1">
          <AppImage
            :src="imageSrc"
            class="size-7 shrink-0"
            :class="{ 'rounded-full overflow-hidden': roundedIcon }"
          />
          <h5 class="m-0 font-medium text-xl text-rui-text">
            {{ title }}
          </h5>
        </div>
      </template>
      <template #left-buttons>
        <slot name="left-buttons" />
      </template>
      <slot />
    </BigDialog>
  </section>
</template>
