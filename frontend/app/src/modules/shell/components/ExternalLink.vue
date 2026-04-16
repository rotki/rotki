<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';
import { useLinks } from '@/modules/shell/layout/use-links';

defineOptions({
  inheritAttrs: false,
});

const {
  confirm = false,
  custom = false,
  premium = false,
  text = '',
  truncate = false,
  url,
} = defineProps<{
  url?: string;
  truncate?: boolean;
  text?: string;
  custom?: boolean;
  premium?: boolean;
  confirm?: boolean;
}>();

defineSlots<{
  default: () => any;
  append: () => any;
}>();

const { isPackaged, openUrl } = useInterop();
const { t } = useI18n({ useScope: 'global' });

const { href, linkTarget, onLinkClick: defaultOnLinkClick } = useLinks(() => url);

const displayText = computed<string>(() => (truncate ? truncateAddress(text) : text));

const targetUrl = computed<string>(() => url ?? externalLinks.premium);

const showConfirmation = ref<boolean>(false);

async function onLinkClick(event?: Event): Promise<void> {
  // If confirm is not enabled, use default behavior
  if (!confirm) {
    defaultOnLinkClick();
    return;
  }

  // Prevent default navigation
  if (event)
    event.preventDefault();

  // Show confirmation dialog
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
  <RuiButton
    v-if="(url || premium) && !custom"
    :tag="isPackaged ? 'button' : 'a'"
    :href="href"
    :target="linkTarget"
    v-bind="$attrs"
    variant="text"
    class="!inline !text-[1em] !p-0 !px-0.5 !-mx-0.5 !font-[inherit] [&_span]:underline"
    @click="onLinkClick($event)"
  >
    <slot>{{ displayText }}</slot>
    <template
      v-if="$slots.append"
      #append
    >
      <slot name="append" />
    </template>
  </RuiButton>
  <a
    v-else-if="url || premium"
    :href="href"
    :target="linkTarget"
    class="whitespace-nowrap"
    v-bind="$attrs"
    @click="onLinkClick($event)"
  >
    <slot>{{ displayText }}</slot>
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
