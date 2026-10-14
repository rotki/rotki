<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { caveat = true } = defineProps<{
  /** Off for rotki's own formats, which do not change under the user like a third party's export. */
  caveat?: boolean;
}>();

defineSlots<{
  default?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <aside
    class="flex flex-col gap-3 rounded-rui-card border border-rui-divider bg-rui-surface p-4 text-sm leading-relaxed text-rui-text-secondary [&_li]:mt-1 [&_strong]:text-rui-text [&_ul]:m-0 [&_ul]:list-disc [&_ul]:pl-5"
    data-testid="import-source-notes"
  >
    <div class="text-sm font-semibold text-rui-text">
      {{ t('import_data.before_you_import') }}
    </div>
    <div v-if="$slots.default">
      <slot />
    </div>
    <i18n-t
      v-if="caveat"
      scope="global"
      tag="p"
      keypath="import_data.notice"
      class="m-0 text-xs"
      :class="{ 'border-t border-rui-divider pt-3': $slots.default }"
    >
      <template #link>
        <ExternalLink
          color="primary"
          :url="externalLinks.githubNewIssue"
        >
          {{ t('import_data.notice_link') }}
        </ExternalLink>
      </template>
    </i18n-t>
  </aside>
</template>
