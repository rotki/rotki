export interface AssetBalance {
    readonly amount: number | string;
    readonly usd_value: number | string;
    readonly percentage?: string;

    readonly [asset: string]: string | number | undefined;
}
