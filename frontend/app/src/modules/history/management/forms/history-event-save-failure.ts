import type { InjectionKey, Ref } from 'vue';

/**
 * Where a history event form names a save that failed with no field to blame.
 *
 * @remarks
 * The dialog owns it and shows it above the form, so the seven forms between them do not each have
 * to hand it up. A form rendered outside the dialog gets a slot of its own that nothing shows.
 */
export const HistoryEventSaveFailureKey: InjectionKey<Ref<string | undefined>> = Symbol('history-event-save-failure');
