<script setup lang="ts">
import { type WelcomeMessage } from '@/types/dynamic-messages';
import { api } from '@/services/rotkehlchen-api';

const props = defineProps<{
  message: WelcomeMessage;
}>();

const { message } = toRefs(props);

const svg = ref();

const link = useRefMap(message, message => message.action?.url || '');

const fetchSvg = async () => {
  const url = props.message.icon;

  if (
    !url ||
    !(
      checkIfDevelopment() ||
      url.startsWith(`https://raw.githubusercontent.com/rotki/data`)
    )
  ) {
    return;
  }

  try {
    const response = await api.instance.get(url);
    return response.data;
  } catch (e: any) {
    logger.error(e);
    return null;
  }
};

watch(message, async (value, oldValue) => {
  if (value.icon && oldValue.icon !== value.icon) {
    set(svg, await fetchSvg());
  }
});

onMounted(async () => {
  if (props.message.icon) {
    set(svg, await fetchSvg());
  }
});

const css = useCssModule();
</script>

<template>
  <div class="flex flex-col align-start gap-4 w-full p-6" :class="css.card">
    <div v-if="message.icon" class="bg-white rounded-[0.625rem] p-3">
      <div
        class="object-contain text-rui-primary h-6 w-6"
        :class="css.icon"
        v-html="svg"
      />
    </div>
    <div v-if="message.header" class="text-h6 text-rui-text">
      {{ message.header }}
    </div>
    <div class="text-body-1 text-rui-text-secondary">
      {{ message.text }}
    </div>

    <ExternalLink v-if="message.action" :url="link" custom>
      <RuiButton color="primary">
        {{ message.action.text }}
      </RuiButton>
    </ExternalLink>
  </div>
</template>

<style module lang="scss">
.card {
  background: rgba(78, 91, 166, 0.04);
}

.icon {
  svg {
    path {
      fill: rgb(var(--rui-primary-main)) !important;
    }
  }
}
</style>
