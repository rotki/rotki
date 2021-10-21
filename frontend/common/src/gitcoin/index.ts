import { BigNumber, Nullable } from "../index";

interface GitcoinBaseEventsPayload {
  readonly fromTimestamp: number;
  readonly toTimestamp: number;
}

interface FromCacheGitcoinEventsPayload extends GitcoinBaseEventsPayload {
  readonly onlyCache: true;
}

export interface GitcoinGrantPayload extends GitcoinBaseEventsPayload {
  readonly grantId: number;
}

export type GitcoinGrantEventsPayload =
  | GitcoinGrantPayload
  | FromCacheGitcoinEventsPayload;

export type GitcoinReportPayload = GitcoinBaseEventsPayload & {
  readonly grantId?: number;
};

export interface GitcoinGrant {
  readonly name: string;
  readonly events: GitcoinGrantEvents[];
  readonly createdOn: string;
}

export interface GitcoinGrants {
  readonly [grantId: string]: GitcoinGrant;
}

interface GitcoinGrantEvents {
  readonly timestamp: number;
  readonly asset: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
  readonly grantId: number;
  readonly txId: string;
  readonly txType: 'ethereum' | 'zksync';
  readonly clrRound: Nullable<number>;
}

export interface GitcoinGrantEarnings {
  readonly amount: BigNumber;
  readonly value: BigNumber;
}

export interface GitcoinGrantPerAssetDetails {
  readonly [asset: string]: GitcoinGrantEarnings;
}

export interface GitcoinGrantDetails {
  readonly perAsset: GitcoinGrantPerAssetDetails;
  readonly total: BigNumber;
}

interface GitcoinPerGrantReport {
  [grantId: string]: GitcoinGrantDetails;
}

export interface GitcoinGrantReport {
  readonly profitCurrency: string;
  readonly reports: GitcoinPerGrantReport;
}
