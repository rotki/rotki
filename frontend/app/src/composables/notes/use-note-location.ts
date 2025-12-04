import type { ComputedRef } from 'vue';

export function useNoteLocation(): ComputedRef<string> {
  const route = useRoute();

  return computed<string>(() => {
    const meta = route.meta;

    if (meta && meta.noteLocation)
      return meta.noteLocation.toString();

    let noteLocation = '';
    route.matched.forEach((matched) => {
      if (matched.meta.noteLocation)
        noteLocation = matched.meta.noteLocation.toString();
    });

    return noteLocation;
  });
}
