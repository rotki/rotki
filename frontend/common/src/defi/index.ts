import { Balance } from "../index";

export interface ProfitLossModel {
  readonly address: string;
  readonly asset: string;
  readonly value: Balance;
}