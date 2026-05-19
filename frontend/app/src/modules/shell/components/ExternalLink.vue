<script setup lang="ts">
import type { ContextColorsType } from '@rotki/ui-library';
import { externalLinks } from '@shared/external-links';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';
import { useLinks } from '@/modules/shell/layout/use-links';

defineOptions({
  inheritAttrs: false,
});

const {
  color = 'primary',
  confirm = false,
  custom = false,
  premium = false,
  text = '',
  url,
} = defineProps<{
  url?: string;
  text?: string;
  custom?: boolean;
  premium?: boolean;
  confirm?: boolean;
  color?: ContextColorsType;
}>();

defineSlots<{
  default: () => any;
}>();

const showConfirmation = ref<boolean>(false);

const { isPackaged, openUrl } = useInterop();
const { t } = useI18n({ useScope: 'global' });

const { href, linkTarget, onLinkClick: defaultOnLinkClick } = useLinks(() => url);

const targetUrl = computed<string>(() => url ?? externalLinks.premium);

const colorClass = computed<string>(() => {
  const map: Record<ContextColorsType, string> = {
    error: 'text-rui-error hover:text-rui-error-darker',
    info: 'text-rui-info hover:text-rui-info-darker',
    primary: 'text-rui-primary hover:text-rui-primary-darker',
    secondary: 'text-rui-secondary hover:text-rui-secondary-darker',
    success: 'text-rui-success hover:text-rui-success-darker',
    warning: 'text-rui-warning hover:text-rui-warning-darker',
  };
  return map[color] ?? map.primary;
});

async function onLinkClick(event?: Event): Promise<void> {
  if (!confirm) {
    defaultOnLinkClick();
    return;
  }

  if (event)
    event.preventDefault();

  set(showConfirmation, true);
}

async function confirmOpen(): Promise<void> {
  set(showConfirmation, false);
  await openUrl(get(targetUrl));
}

function cancelOpen(): void {
  set(showConfirmation, false);
}
</script>

<template>
  <component
    :is="isPackaged ? 'button' : 'a'"
    v-if="(url || premium) && !custom"
    :href="isPackaged ? undefined : href"
    :target="linkTarget"
    :type="isPackaged ? 'button' : undefined"
    v-bind="$attrs"
    class="cursor-pointer underline"
    :class="colorClass"
    @click="onLinkClick($event)"
  >
    <slot>{{ text }}</slot>
  </component>
  <a
    v-else-if="url || premium"
    :href="href"
    :target="linkTarget"
    class="whitespace-nowrap"
    v-bind="$attrs"
    @click="onLinkClick($event)"
  >
    <slot>{{ text }}</slot>
  </a>
  <div
    v-else
    v-bind="$attrs"
  >
    <slot />
  </div>

  <ConfirmDialog
    v-if="confirm"
    :display="showConfirmation"
    :title="t('common.external_link_confirmation.title')"
    :message="t('common.external_link_confirmation.message')"
    confirm-type="info"
    @confirm="confirmOpen()"
    @cancel="cancelOpen()"
  >
    <div class="mt-4">
      <div class="text-rui-text-secondary text-caption">
        {{ t('common.url') }}:
      </div>
      <div class="font-bold break-all">
        {{ targetUrl }}
      </div>
    </div>
  </ConfirmDialog>
</template>
