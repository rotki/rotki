import { Section, Status } from '@/store/const';

type ActionFailure = {
  readonly message: string;
  readonly success: false;
};

type ActionSuccess = {
  readonly success: true;
};

export type ActionStatus = ActionFailure | ActionSuccess;

export interface StatusPayload {
  readonly status: Status;
  readonly section: Section;
}

export interface Version {
  readonly version: string;
  readonly latestVersion: string;
  readonly downloadUrl: string;
}

export type ActionDataEntry<T = string> = {
  readonly identifier: T;
  readonly label: string;
  readonly icon?: string | undefined;
  readonly image?: string | undefined;
  readonly color?: string | undefined;
  readonly matcher?: (identifier: string) => boolean | undefined;
  readonly detailPath?: string | undefined;
};
