import {
	type ColumnDef,
	flexRender,
	getCoreRowModel,
	useReactTable,
} from "@tanstack/react-table";
import { useMemo } from "react";
import type {
	RowMajorTable,
	TableCell,
} from "@/lib/transforms/tableToRowMajor";
import { cn } from "@/lib/utils";

export type DocTableProps = {
	table: RowMajorTable;
	className?: string;
};

type Row = { label: string; values: TableCell[] };

const STICKY_FIRST_COLUMN_STYLE: React.CSSProperties = {
	position: "sticky",
	left: 0,
	background: "var(--color-card)",
};

export function DocTable({ table, className }: DocTableProps) {
	const rows = useMemo<Row[]>(
		() =>
			table.rowLabels.map((label, rowIndex) => ({
				label,
				values: table.data[rowIndex] ?? [],
			})),
		[table.rowLabels, table.data],
	);

	const columns = useMemo<ColumnDef<Row>[]>(() => {
		const labelColumn: ColumnDef<Row> = {
			id: "__row_label",
			header: "",
			cell: ({ row }) => row.original.label,
		};
		const valueColumns = table.columns.map<ColumnDef<Row>>(
			(columnName, index) => ({
				id: `${index}:${columnName}`,
				header: columnName,
				accessorFn: (row) => row.values[index] ?? null,
			}),
		);
		return [labelColumn, ...valueColumns];
	}, [table.columns]);

	const reactTable = useReactTable({
		data: rows,
		columns,
		getCoreRowModel: getCoreRowModel(),
	});

	return (
		<div
			data-testid="doc-table"
			className={cn(
				"relative w-full overflow-x-auto rounded-md border border-border bg-card",
				className,
			)}
		>
			<table className="w-full border-collapse text-sm">
				<thead>
					{reactTable.getHeaderGroups().map((headerGroup) => (
						<tr key={headerGroup.id}>
							{headerGroup.headers.map((header, headerIndex) => {
								const isFirst = headerIndex === 0;
								return (
									<th
										key={header.id}
										scope="col"
										data-testid={
											isFirst ? "doc-table-header-label" : "doc-table-header"
										}
										style={isFirst ? STICKY_FIRST_COLUMN_STYLE : undefined}
										className={cn(
											"break-words border-b border-border px-3 py-2 text-left align-bottom text-xs font-medium uppercase tracking-wide text-muted-foreground",
											"whitespace-normal",
											isFirst ? "z-10 min-w-40" : "min-w-28 text-right",
										)}
									>
										{header.isPlaceholder
											? null
											: flexRender(
													header.column.columnDef.header,
													header.getContext(),
												)}
									</th>
								);
							})}
						</tr>
					))}
				</thead>
				<tbody>
					{reactTable.getRowModel().rows.map((row) => (
						<tr key={row.id} className="border-b border-border last:border-b-0">
							{row.getVisibleCells().map((cell, cellIndex) => {
								const isFirst = cellIndex === 0;
								if (isFirst) {
									return (
										<th
											key={cell.id}
											scope="row"
											data-testid="doc-table-row-label"
											style={STICKY_FIRST_COLUMN_STYLE}
											className="z-10 break-words px-3 py-2 text-left text-sm font-normal text-foreground"
										>
											{flexRender(
												cell.column.columnDef.cell,
												cell.getContext(),
											)}
										</th>
									);
								}
								const value = cell.getValue<TableCell>();
								const isNumeric = typeof value === "number";
								return (
									<td
										key={cell.id}
										data-testid="doc-table-cell"
										className={cn(
											"px-3 py-2 align-top text-sm",
											isNumeric
												? "numeric text-right text-foreground"
												: "text-left text-muted-foreground",
										)}
									>
										{formatCell(value)}
									</td>
								);
							})}
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

function formatCell(value: TableCell): string {
	if (value === null) return "—";
	if (typeof value === "number") return formatNumber(value);
	return value;
}

const NUMBER_FORMATTER = new Intl.NumberFormat("en-US", {
	maximumFractionDigits: 4,
});

function formatNumber(value: number): string {
	if (!Number.isFinite(value)) return String(value);
	return NUMBER_FORMATTER.format(value);
}
