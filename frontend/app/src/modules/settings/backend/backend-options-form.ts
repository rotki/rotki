import type { BackendOptions } from '@shared/ipc';
import type { DefaultBackendArguments } from '@/modules/shell/app/backend';
import { isEqual } from 'es-toolkit';
import { z, type ZodType } from 'zod';

/** The three numeric settings that carry a reset-to-default button. */
export type AdvancedBackendField = 'files' | 'size' | 'instructions';

/**
 * The onboarding form holds its three numeric settings as strings, because the
 * inputs are text fields. These are the raw field values, before parsing.
 */
export interface BackendOptionsFormFields {
  dataDirectory: string;
  logDirectory: string;
  logFromOtherModules: boolean;
  loglevel: BackendOptions['loglevel'];
  maxLogFiles: string;
  maxLogSize: string;
  sqliteInstructions: string;
}

/**
 * Parses a numeric field. A blank or unparsable value counts as 0, and a
 * fractional value is truncated rather than rejected.
 */
export function parseValue(value?: string): number {
  if (!value)
    return 0;

  const parsedValue = Number.parseInt(value);
  return Number.isNaN(parsedValue) ? 0 : parsedValue;
}

export function stringifyValue(value?: number): string {
  if (!value)
    return '0';

  return value.toString();
}

/**
 * Projects the raw fields onto the option shape, so they can be compared with
 * the initial options field by field.
 */
export function toBackendOptions(fields: BackendOptionsFormFields): Partial<BackendOptions> {
  return {
    dataDirectory: fields.dataDirectory,
    logDirectory: fields.logDirectory,
    logFromOtherModules: fields.logFromOtherModules,
    loglevel: fields.loglevel,
    maxLogfilesNum: parseValue(fields.maxLogFiles),
    maxSizeInMbAllLogs: parseValue(fields.maxLogSize),
    sqliteInstructions: parseValue(fields.sqliteInstructions),
  };
}

/**
 * The options that differ from the initial ones. Only these are sent, so the
 * backend keeps whatever the user did not touch.
 */
export function diffBackendOptions(
  fields: BackendOptionsFormFields,
  initial: Partial<BackendOptions>,
): Partial<BackendOptions> {
  const current = toBackendOptions(fields);
  const changed: Partial<BackendOptions> = {};

  if (current.loglevel !== initial.loglevel)
    changed.loglevel = current.loglevel;

  if (current.dataDirectory !== initial.dataDirectory)
    changed.dataDirectory = current.dataDirectory;

  if (current.logDirectory !== initial.logDirectory)
    changed.logDirectory = current.logDirectory;

  if (current.logFromOtherModules !== initial.logFromOtherModules)
    changed.logFromOtherModules = current.logFromOtherModules;

  if (current.maxLogfilesNum !== initial.maxLogfilesNum)
    changed.maxLogfilesNum = current.maxLogfilesNum;

  if (current.maxSizeInMbAllLogs !== initial.maxSizeInMbAllLogs)
    changed.maxSizeInMbAllLogs = current.maxSizeInMbAllLogs;

  if (current.sqliteInstructions !== initial.sqliteInstructions)
    changed.sqliteInstructions = current.sqliteInstructions;

  return changed;
}

export function hasBackendOptionChanges(
  fields: BackendOptionsFormFields,
  initial: Partial<BackendOptions>,
): boolean {
  return !isEqual(toBackendOptions(fields), initial);
}

/** The three validated fields, which are the only ones the form schema covers. */
export interface BackendNumericFields {
  maxLogFiles: string;
  maxLogSize: string;
  sqliteInstructions: string;
}

export type BackendNumericField = keyof BackendNumericFields;

export interface BackendNumericMessages {
  /** Already translated, not i18n keys: the bound message interpolates its own minimum. */
  nonEmpty: string;
  min: string;
}

/**
 * Digits with an optional fractional part, and no sign. This is vuelidate's
 * `numeric` is kept verbatim: it is the rule that actually rejects a bad value, because a signed
 * value never reaches the `minValue(0)` it was paired with. Loosening it to a plain "is a number and
 * not negative" would accept exponent notation, which `parseValue` then truncates to its mantissa.
 */
const DIGITS = /^\d*(?:\.\d+)?$/;

function backendNumericField(messages: BackendNumericMessages): ZodType<string> {
  return z.string().superRefine((value, ctx) => {
    if (!DIGITS.test(value))
      ctx.addIssue({ code: 'custom', message: messages.min });

    if (value.trim() === '')
      ctx.addIssue({ code: 'custom', message: messages.nonEmpty });
  });
}

export function backendNumericSchema(messages: BackendNumericMessages): ZodType {
  const field = backendNumericField(messages);
  return z.object({
    maxLogFiles: field,
    maxLogSize: field,
    sqliteInstructions: field,
  });
}

/**
 * Whether the three resettable numeric fields still hold their default, which
 * is what hides each field's reset button.
 */
export function backendDefaultsState(
  fields: Pick<BackendOptionsFormFields, 'maxLogFiles' | 'maxLogSize' | 'sqliteInstructions'>,
  defaults: DefaultBackendArguments,
): { maxLogFiles: boolean; maxLogSize: boolean; sqliteInstructions: boolean } {
  return {
    maxLogFiles: defaults.maxLogfilesNum === parseValue(fields.maxLogFiles),
    maxLogSize: defaults.maxSizeInMbAllLogs === parseValue(fields.maxLogSize),
    sqliteInstructions: defaults.sqliteInstructions === parseValue(fields.sqliteInstructions),
  };
}
