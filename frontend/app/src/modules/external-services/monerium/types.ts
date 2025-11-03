export interface MoneriumProfile {
  id: string;
  kind?: string;
  name?: string;
}

export interface MoneriumStatus {
  authenticated: boolean;
  defaultProfileId?: string;
  expiresAt?: number;
  profiles?: MoneriumProfile[];
  tokenType?: string;
  userEmail?: string;
}

export interface MoneriumAuthResult {
  defaultProfileId?: string;
  message: string;
  profiles?: MoneriumProfile[];
  success: boolean;
  userEmail?: string;
}

export type MoneriumOAuthResult = Omit<MoneriumAuthResult, 'success'>;
