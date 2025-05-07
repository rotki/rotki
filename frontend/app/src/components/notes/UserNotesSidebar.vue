<script setup lang="ts">
import UserNotesList from '@/components/notes/UserNotesList.vue';
import { useAppRoutes } from '@/router/routes';
import { NoteLocation } from '@/types/notes';

const display = defineModel<boolean>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const tab = ref<number>(0);

const route = useRoute();

const openDialog = ref<boolean>(false);

const location = computed<string>(() => {
  const meta = get(route).meta;

  if (meta && meta.noteLocation)
    return meta.noteLocation.toString();

  let noteLocation = '';
  get(route).matched.forEach((matched) => {
    if (matched.meta.noteLocation)
      noteLocation = matched.meta.noteLocation.toString();
  });

  return noteLocation;
});

const { appRoutes } = useAppRoutes();

function getNoteLocationKey(key: string): string | null {
  const index = Object.values<string>(NoteLocation).indexOf(key);
  if (index > -1)
    return Object.keys(NoteLocation)[index];

  return null;
}

const locationName = computed<string>(() => {
  const locationVal = get(location);
  if (!locationVal)
    return '';

  const noteLocationKey = getNoteLocationKey(locationVal);
  if (!noteLocationKey)
    return '';

  const Routes = get(appRoutes);
  const keyIn = (key: string): key is keyof typeof Routes => key in Routes;

  if (keyIn(noteLocationKey))
    return Routes[noteLocationKey].text;

  return '';
});

watch(locationName, (locationName) => {
  if (locationName === '')
    set(tab, 0);
});
</script>

<template>
  <RuiNavigationDrawer
    v-model="display"
    width="460px"
    temporary
    :stateless="openDialog"
    position="right"
  >
    <div class="flex items-center justify-between gap-2 w-full border-b border-default">
      <RuiTabs
        v-model="tab"
        class="tabs"
        color="primary"
      >
        <RuiTab>
          {{ t('notes_menu.tabs.general') }}
        </RuiTab>
        <RuiTab v-if="locationName">
          <RuiTooltip
            :popper="{ placement: 'bottom' }"
            :open-delay="400"
          >
            <template #activator>
              {{ t('notes_menu.tabs.in_this_page', { page: locationName }) }}
            </template>
            {{
              t('notes_menu.tabs.in_this_page_tooltip', {
                page: locationName,
              })
            }}
          </RuiTooltip>
        </RuiTab>
      </RuiTabs>

      <RuiButton
        class="!p-2"
        variant="text"
        icon
        @click="display = false"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>

    <UserNotesList
      v-if="display"
      :key="location + tab"
      v-model:open="openDialog"
      :location="tab === 0 ? '' : location"
    />
  </RuiNavigationDrawer>
</template>
