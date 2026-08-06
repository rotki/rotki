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

// The backend sends icon/color as free-form strings; only their runtime shape can be
// validated, so `z.custom` keeps the parsed type aligned with ActionDataEntry.
const isString = (value: unknown): boolean => typeof value === 'string';

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
