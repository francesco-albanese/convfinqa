import type {
	RowMajorTable,
	TableCell,
} from "@/lib/transforms/tableToRowMajor";

const RFC_4180_LINE_ENDING = "\r\n";
const FORMULA_PREFIXES = ["=", "+", "-", "@", "\t", "\r"];

export function rowMajorToCsv(table: RowMajorTable): string {
	const header = ["", ...table.columns].map(toCsvHeader).join(",");
	const rows = table.rowLabels.map((label, rowIndex) => {
		const cells = table.data[rowIndex] ?? [];
		const fields = [label, ...table.columns.map((_, i) => cells[i] ?? null)];
		return fields.map(toCsvField).join(",");
	});
	return [header, ...rows].join(RFC_4180_LINE_ENDING);
}

function toCsvHeader(value: string): string {
	return escapeCsvField(neutraliseFormulaPrefix(value));
}

function toCsvField(value: TableCell): string {
	if (value === null) return "";
	if (typeof value === "number") return escapeCsvField(String(value));
	return escapeCsvField(neutraliseFormulaPrefix(value));
}

function neutraliseFormulaPrefix(value: string): string {
	if (value.length === 0) return value;
	const firstChar = value.charAt(0);
	return FORMULA_PREFIXES.includes(firstChar) ? `'${value}` : value;
}

function escapeCsvField(value: string): string {
	if (/[",\r\n]/.test(value)) {
		return `"${value.replace(/"/g, '""')}"`;
	}
	return value;
}
