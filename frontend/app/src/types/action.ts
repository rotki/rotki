import { type ContextColorsType } from '@rotki/ui-library-compat';
import { type Section, type Status } from '@/types/status';

interface ActionFailure<T = string> {
  readonly message: T;
  readonly success: false;
}

export interface ActionSuccess {
  readonly success: true;
}

export type ActionStatus<T = string> = ActionFailure<T> | ActionSuccess;

export interface StatusPayload {
  readonly status: Status;
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
  readonly icon?: string | null;
  readonly image?: string | null;
  readonly color?: ContextColorsType;
  readonly matcher?: (identifier: string) => boolean | null;
  readonly detailPath?: string | null;
}
