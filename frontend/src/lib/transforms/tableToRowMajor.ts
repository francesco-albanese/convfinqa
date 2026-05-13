export type TableCell = number | string | null;

export type TableInput = Record<string, Record<string, TableCell>>;

export type RowMajorTable = {
	columns: string[];
	rowLabels: string[];
	data: TableCell[][];
};

export function tableToRowMajor(input: TableInput): RowMajorTable {
	const columns = Object.keys(input);

	const seen = new Set<string>();
	const rowLabels: string[] = [];
	for (const column of columns) {
		const cells = input[column];
		if (!cells) continue;
		for (const label of Object.keys(cells)) {
			if (!seen.has(label)) {
				seen.add(label);
				rowLabels.push(label);
			}
		}
	}

	const data = rowLabels.map((label) =>
		columns.map((column) => {
			const cells = input[column];
			if (!cells || !Object.hasOwn(cells, label)) return null;
			const value = cells[label];
			return value === undefined ? null : value;
		}),
	);

	return { columns, rowLabels, data };
}
