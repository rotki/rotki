import type { ContextColorsType, RuiIcons } from '@rotki/ui-library';
import type { Section, Status } from '@/types/status';
import { z } from 'zod/v4';

interface ActionFailure<T = string> {
  readonly message: T;
  readonly success: false;
}

interface ActionSuccess {
  readonly success: true;
}

export type ActionStatus<T = string> = ActionFailure<T> | ActionSuccess;

export interface StatusPayload {
  readonly status: Status;
  readonly subsection?: string;
  readonly section: Section;
}

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

const ActionDataEntrySchema = z.object({
  identifier: z.string(),
  label: z.string(),
  icon: z.string().optional(),
  image: z.string().optional(),
  darkmodeImage: z.string().optional(),
  color: z.string().optional(),
  detailPath: z.string().optional(),
});

export const ActionDataEntryArraySchema = z.array(ActionDataEntrySchema);
