import type { ContextColorsType, RuiIcons } from '@rotki/ui-library';
import { z } from 'zod';

interface ActionFailure<T = string> {
  readonly message: T;
  readonly success: false;
}

interface ActionSuccess {
  readonly success: true;
}

export type ActionStatus<T = string> = ActionFailure<T> | ActionSuccess;

export interface Version {
  readonly version: string;
  readonly latestVersion: string;
  readonly downloadUrl: string;
}

export interface ActionDataEntry<T = string> {
  readonly identifier: T;
  readonly label: string;
  readonly icon?: RuiIcons;
  readonly image?: string;
  readonly darkmodeImage?: string;
  readonly color?: ContextColorsType;
  readonly matcher?: (identifier: string) => boolean | null;
  readonly detailPath?: string;
}

const isString = (value: unknown): boolean => typeof value === 'string';

/**
 * Parses one action data entry off the wire.
 *
 * @remarks
 * The backend sends `icon` and `color` as free-form strings, so `z.custom` validates the runtime
 * shape only while keeping the parsed type assignable to {@link ActionDataEntry}.
 */
const ActionDataEntrySchema = z.object({
  identifier: z.string(),
  label: z.string(),
  icon: z.custom<RuiIcons>(isString).optional(),
  image: z.string().optional(),
  darkmodeImage: z.string().optional(),
  color: z.custom<ContextColorsType>(isString).optional(),
  detailPath: z.string().optional(),
});

export const ActionDataEntryArraySchema = z.array(ActionDataEntrySchema);
