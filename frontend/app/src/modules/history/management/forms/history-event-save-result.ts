import type { Result } from 'plainfp/result';

/**
 * How a history event form's save went, handed up through each form's exposed `save`.
 *
 * @remarks
 * An `Err` carries the message of a failure no field is to blame for, which the dialog shows above
 * the form, or `undefined` when the fields already say what is wrong (validation, or the API's
 * field errors).
 */
export type HistoryEventSaveResult = Result<void, string | undefined>;
