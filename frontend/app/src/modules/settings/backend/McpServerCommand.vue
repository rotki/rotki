<script setup lang="ts">
import type { McpServerInfo } from '@/modules/shell/app/backend';
import { startPromise } from '@shared/utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import CopyTooltip from '@/modules/shell/components/CopyTooltip.vue';

const { t } = useI18n({ useScope: 'global' });

const { mcpServerInfo } = useSettingsApi();

const info = ref<McpServerInfo>();
const error = ref<string>();
const loading = ref<boolean>(false);

const displayCommand = computed<string>(() => {
  const mcpInfo = get(info);
  return mcpInfo?.available ? mcpInfo.displayCommand : '';
});

async function loadMcpInfo(): Promise<void> {
  set(loading, true);
  set(error, undefined);

  try {
    set(info, await mcpServerInfo());
  }
  catch (error_: unknown) {
    set(error, getErrorMessage(error_));
  }
  finally {
    set(loading, false);
  }
}

onBeforeMount(() => {
  startPromise(loadMcpInfo());
});
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('backend_settings.settings.mcp_command.label') }}
    </template>
    <template #subtitle>
      {{ t('backend_settings.settings.mcp_command.hint') }}
    </template>

    <RuiAlert
      v-if="error"
      type="error"
    >
      {{ t('backend_settings.settings.mcp_command.load_error', { message: error }) }}
    </RuiAlert>

    <div
      v-else-if="loading"
      class="text-rui-text-secondary"
    >
      {{ t('backend_settings.settings.mcp_command.loading') }}
    </div>

    <RuiAlert
      v-else-if="info && !info.available"
      type="info"
    >
      <div class="font-medium">
        {{ t('backend_settings.settings.mcp_command.unavailable') }}
      </div>
      <div class="mt-1">
        {{ info.reason }}
      </div>
    </RuiAlert>

    <div
      v-else-if="info && info.available"
      class="flex items-start gap-2 rounded border border-default bg-rui-grey-50 dark:bg-rui-grey-900 p-3"
    >
      <code class="flex-1 min-w-0 text-sm break-all font-mono">
        {{ displayCommand }}
      </code>
      <CopyTooltip :value="displayCommand">
        <RuiButton
          icon
          variant="text"
          color="primary"
          size="sm"
        >
          <RuiIcon
            name="lu-copy"
            size="16"
          />
        </RuiButton>
        <template #label>
          {{ t('common.actions.copy_to_clipboard') }}
        </template>
      </CopyTooltip>
    </div>
  </SettingsItem>
</template>
