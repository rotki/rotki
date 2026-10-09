<script setup lang="ts">
import type { SystemVersion } from '@shared/ipc';
import type { WebVersion } from '@/types';
import { millisecondsToSeconds } from '@/modules/core/common/data/date';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { usePremium } from '@/modules/premium/use-premium';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import AboutDataDirectory from '@/modules/shell/components/AboutDataDirectory.vue';
import AppUpdateIndicator from '@/modules/shell/components/AppUpdateIndicator.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import RotkiLogo from '@/modules/shell/components/RotkiLogo.vue';
import { isWebVersion, useVersionText } from '@/modules/shell/components/use-version-text';

interface DetailRow {
  label: string;
  value: string;
  testId?: string;
}

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const store = useMainStore();
const { isPackaged, openPath, version: getVersion } = useInterop();

const { dataDirectory, version } = toRefs(store);
const versionInfo = asyncComputed<SystemVersion | WebVersion>(() => getVersion());

const premium = usePremium();
const componentsVersion = computed(() => {
  if (!get(premium))
    return null;

  const cmp = window.PremiumComponents;
  if (!cmp)
    return null;

  return {
    build: cmp.build,
    version: cmp.version,
  };
});

const frontendVersion = __APP_VERSION__;

/** The plain-text rows below the data directory, in the order the copied text lists them. */
const systemRows = computed<DetailRow[]>(() => {
  const rows: DetailRow[] = [{ label: t('about.frontend_version'), value: frontendVersion }];
  const info = get(versionInfo);
  if (!info)
    return rows;

  if (isWebVersion(info)) {
    rows.push(
      { label: t('about.platform'), testId: 'about-web-platform', value: info.platform },
      { label: t('about.user_agent'), testId: 'about-user-agent', value: info.userAgent },
    );
  }
  else {
    rows.push(
      { label: t('about.platform'), testId: 'about-electron-platform', value: `${info.os} ${info.arch} ${info.osVersion}` },
      { label: t('about.electron'), testId: 'about-electron-version', value: info.electron },
    );
  }
  return rows;
});

const versionText = useVersionText(() => ({
  appVersion: get(version).version,
  components: get(componentsVersion) ?? undefined,
  frontendVersion,
  system: get(versionInfo) ?? undefined,
}));

const { copied, copy } = useClipboard({ source: versionText });
</script>

<template>
  <RuiCard
    variant="flat"
    no-padding
  >
    <template #custom-header>
      <div class="flex items-center gap-4 px-6 pt-6 pb-4">
        <span class="rounded-full p-2.5 bg-rui-primary/20 shrink-0">
          <RotkiLogo
            size="2"
            unique-key="00"
          />
        </span>
        <div class="grow min-w-0">
          <h2 class="text-h5">
            {{ t('app.name') }}
          </h2>
          <p class="text-body-2 text-rui-text-secondary">
            {{ t('app.moto') }}
          </p>
        </div>
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="self-start -mt-2 -me-2"
          :aria-label="t('common.actions.close')"
          @click="emit('close')"
        >
          <RuiIcon
            name="lu-x"
            size="20"
          />
        </RuiButton>
      </div>
    </template>

    <div class="px-6 pb-2">
      <div class="flex items-center gap-3 rounded-lg bg-rui-grey-100 dark:bg-rui-grey-900 px-4 py-3">
        <div class="grow min-w-0">
          <div class="text-caption uppercase tracking-wide text-rui-text-secondary">
            {{ t('about.version') }}
          </div>
          <div class="font-medium break-all">
            {{ version.version }}
          </div>
        </div>
        <ExternalLink
          class="shrink-0 text-body-2"
          :url="`https://github.com/rotki/rotki/releases/tag/v${version.version}`"
          :text="t('about.release_notes')"
        />
        <AppUpdateIndicator />
      </div>

      <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-2.5 text-body-2 pt-5 pb-2">
        <dt class="text-rui-text-secondary">
          {{ t('about.data_directory') }}
        </dt>
        <dd class="min-w-0 -my-1">
          <AboutDataDirectory
            :data-directory="dataDirectory"
            :is-packaged="isPackaged"
            @open-path="openPath(dataDirectory)"
          />
        </dd>
        <template
          v-for="row in systemRows"
          :key="row.label"
        >
          <dt class="text-rui-text-secondary">
            {{ row.label }}
          </dt>
          <dd
            class="break-words"
            :data-testid="row.testId"
          >
            {{ row.value }}
          </dd>
        </template>
      </dl>

      <template v-if="componentsVersion">
        <h3 class="text-subtitle-2 border-t border-default mt-3 pt-4 mb-2">
          {{ t('about.components.title') }}
        </h3>
        <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-2.5 text-body-2 pb-2">
          <template v-if="componentsVersion.version">
            <dt class="text-rui-text-secondary">
              {{ t('about.components.version') }}
            </dt>
            <dd data-testid="about-components-version">
              {{ componentsVersion.version }}
            </dd>
          </template>
          <template v-if="componentsVersion.build">
            <dt class="text-rui-text-secondary">
              {{ t('about.components.build') }}
            </dt>
            <dd data-testid="about-components-build">
              <DateDisplay :timestamp="millisecondsToSeconds(componentsVersion.build)" />
            </dd>
          </template>
        </dl>
      </template>
    </div>

    <template #footer>
      <div class="flex justify-end w-full px-2 pb-2">
        <RuiButton
          color="primary"
          variant="outlined"
          data-testid="about-copy"
          @click="copy()"
        >
          <template #prepend>
            <RuiIcon
              size="18"
              :name="copied ? 'lu-check' : 'lu-copy'"
            />
          </template>
          {{ t('about.copy_information_tooltip') }}
        </RuiButton>
      </div>
    </template>
  </RuiCard>
</template>
