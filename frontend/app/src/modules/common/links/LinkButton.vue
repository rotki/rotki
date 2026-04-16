<script setup lang="ts">
import { useLinks } from '@/composables/links';
import { truncateAddress } from '@/modules/common/display/truncate';

const { base, text, isToken } = defineProps<{
  base: string;
  text: string;
  size: string | number;
  isToken: boolean;
}>();

const url = computed<string>(() => {
  const linkText = isToken ? text.replace('/', '?a=') : text;
  return base + linkText;
});

const displayUrl = computed<string>(() => base + truncateAddress(text, 10));

const { href, onLinkClick } = useLinks(url);
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip

    :popper="{ placement: 'top' }"
    :open-delay="600"
  >
    <template #activator>
      <RuiButton
        tag="a"
        icon
        variant="text"
        class="!bg-rui-grey-200 dark:!bg-rui-grey-900 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800"
        size="sm"
        color="primary"
        :href="href"
        target="_blank"
        @click="onLinkClick()"
      >
        <RuiIcon
          name="lu-external-link"
          :size="size"
        />
      </RuiButton>
    </template>

    {{ t('hash_link.open_link') }}:
    {{ displayUrl }}
  </RuiTooltip>
</template>
