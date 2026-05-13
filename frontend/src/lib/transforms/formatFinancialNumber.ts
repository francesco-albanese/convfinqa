const FINANCIAL_NUMBER_FORMATTER = new Intl.NumberFormat("en-US", {
	maximumFractionDigits: 4,
});

export function formatFinancialNumber(value: number): string {
	if (!Number.isFinite(value)) return String(value);
	return FINANCIAL_NUMBER_FORMATTER.format(value);
}
