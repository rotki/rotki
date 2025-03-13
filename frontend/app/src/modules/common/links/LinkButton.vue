<script setup lang="ts">
import { useLinks } from '@/composables/links';
import { truncateAddress } from '@/utils/truncate';

const props = defineProps<{
  base: string;
  text: string;
  size: string | number;
  isToken: boolean;
}>();

const url = computed<string>(() => {
  const isToken = props.isToken;
  const linkText = isToken ? props.text.replace('/', '?a=') : props.text;
  return props.base + linkText;
});

const displayUrl = computed<string>(() => props.base + truncateAddress(props.text, 10));

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
