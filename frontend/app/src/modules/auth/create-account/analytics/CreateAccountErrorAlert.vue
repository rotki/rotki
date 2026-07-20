<script lang="ts" setup>
import { externalLinks } from '@shared/external-links';
import {
  type ParsedDeviceLimitError,
  parseDeviceLimitError,
} from '@/modules/auth/create-account/analytics/parse-device-limit-error';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { error } = defineProps<{
  error: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const parsedError = computed<ParsedDeviceLimitError>(() => parseDeviceLimitError(error));
</script>

<template>
  <RuiAlert type="error">
    <template v-if="parsedError.hasLink">
      {{ parsedError.parts[0] }}
      <i18n-t keypath="create_account.error.device_limit_link">
        <template #here>
          <ExternalLink
            :url="externalLinks.premiumDevices"
            custom
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n-t>
      {{ parsedError.parts[1] }}
    </template>
    <template v-else>
      {{ error }}
    </template>
  </RuiAlert>
</template>
