<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { useMainStore } from '@/modules/core/common/use-main-store';
import CopyButton from '@/modules/shell/components/CopyButton.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const SESSION_KEY_VARIABLE = 'ROTKI_SESSION_KEY';
const SESSION_KEY_COMMAND = `${SESSION_KEY_VARIABLE}=$(openssl rand -hex 32)`;
const ACCEPT_VARIABLE = 'ROTKI_ACCEPT_UNAUTHENTICATED_API';

const { unauthenticatedApiAccepted } = storeToRefs(useMainStore());
const { t } = useI18n({ useScope: 'global' });
const { dockerSessionAuth } = externalLinks;

function proceed(): void {
  set(unauthenticatedApiAccepted, true);
}
</script>

<template>
  <div class="max-w-[32rem] mx-auto">
    <RuiAlert
      type="warning"
      :title="t('docker_warning.heading')"
    >
      <div class="flex flex-col gap-4">
        <p>{{ t('docker_warning.message') }}</p>

        <i18n-t
          scope="global"
          keypath="docker_warning.recommendation"
          tag="p"
        >
          <code class="font-mono">{{ SESSION_KEY_VARIABLE }}</code>
        </i18n-t>

        <div>
          <p class="mb-1">
            {{ t('docker_warning.command_hint') }}
          </p>
          <div class="flex items-center gap-2 pl-2 rounded bg-rui-grey-100 dark:bg-rui-grey-900">
            <code class="font-mono text-xs break-all grow">{{ SESSION_KEY_COMMAND }}</code>
            <CopyButton
              size="sm"
              :value="SESSION_KEY_COMMAND"
              :tooltip="t('docker_warning.copy_command')"
            />
          </div>
        </div>

        <ExternalLink
          :text="t('docker_warning.docs_link')"
          :url="dockerSessionAuth"
          color="warning"
        />

        <!-- The backend cannot see an upstream proxy, so a correctly protected
             deployment still lands here. Say so rather than calling it unprotected. -->
        <p>{{ t('docker_warning.proxy_note') }}</p>

        <div>
          <RuiButton
            size="sm"
            color="secondary"
            @click="proceed()"
          >
            {{ t('docker_warning.accept') }}
          </RuiButton>
          <!-- The variable stays out of an i18n-t slot: those slots do not render in unit
               tests, and this is the only place the new variable is named. -->
          <p class="mt-2 text-caption">
            {{ t('docker_warning.accept_hint') }}
            <code class="font-mono">{{ ACCEPT_VARIABLE }}</code>
          </p>
        </div>
      </div>
    </RuiAlert>
  </div>
</template>
