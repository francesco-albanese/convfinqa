import { skipToken, useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { z } from "zod";

export const DocumentSummarySchema = z.object({
	id: z.string().min(1),
	ticker: z.string().nullable(),
	year: z.number().int().nullable(),
	page: z.number().int().nullable(),
	title: z.string().nullable(),
});

const TableCellSchema = z.union([z.number(), z.string(), z.null()]);
const TableDataSchema = z.record(
	z.string(),
	z.record(z.string(), TableCellSchema),
);

export const DocumentSchema = DocumentSummarySchema.extend({
	pre_text: z.string().nullable(),
	post_text: z.string().nullable(),
	table_data: TableDataSchema.nullable(),
	column_order: z.array(z.string()).nullable(),
});

export type Document = z.infer<typeof DocumentSchema>;

export const DocumentListPageSchema = z.object({
	items: z.array(DocumentSummarySchema),
	next_cursor: z.string().nullable(),
});

export type DocumentSummary = z.infer<typeof DocumentSummarySchema>;
export type DocumentListPage = z.infer<typeof DocumentListPageSchema>;

export type DocumentListFilters = {
	q?: string;
	yearMin?: number;
	yearMax?: number;
};

const DOCUMENTS_PATH = "/v1/documents";

export function buildDocumentsUrl(
	filters: DocumentListFilters,
	cursor: string | null,
): string {
	const params = new URLSearchParams();
	const trimmedQ = filters.q?.trim();
	if (trimmedQ) {
		params.set("q", trimmedQ);
	}
	if (typeof filters.yearMin === "number") {
		params.set("year_min", String(filters.yearMin));
	}
	if (typeof filters.yearMax === "number") {
		params.set("year_max", String(filters.yearMax));
	}
	if (cursor) {
		params.set("cursor", cursor);
	}
	const qs = params.toString();
	return qs ? `${DOCUMENTS_PATH}?${qs}` : DOCUMENTS_PATH;
}

export async function fetchDocumentList(
	filters: DocumentListFilters,
	cursor: string | null,
): Promise<DocumentListPage> {
	const response = await fetch(buildDocumentsUrl(filters, cursor), {
		headers: { Accept: "application/json" },
	});
	if (!response.ok) {
		throw new Error(
			`fetchDocumentList: ${response.status} ${response.statusText}`,
		);
	}
	return DocumentListPageSchema.parse(await response.json());
}

export function documentsListQueryKey(filters: DocumentListFilters) {
	return [
		"documents",
		"list",
		{
			q: filters.q?.trim() ?? "",
			yearMin: filters.yearMin ?? null,
			yearMax: filters.yearMax ?? null,
		},
	];
}

export function useDocumentList(filters: DocumentListFilters) {
	return useInfiniteQuery({
		queryKey: documentsListQueryKey(filters),
		queryFn: ({ pageParam }) => fetchDocumentList(filters, pageParam),
		initialPageParam: null as string | null,
		getNextPageParam: (lastPage) => lastPage.next_cursor,
	});
}

export function buildDocumentUrl(id: string): string {
	return `${DOCUMENTS_PATH}/${encodeURI(id)}`;
}

export async function fetchDocument(id: string): Promise<Document> {
	const response = await fetch(buildDocumentUrl(id), {
		headers: { Accept: "application/json" },
	});
	if (!response.ok) {
		throw new Error(`fetchDocument: ${response.status} ${response.statusText}`);
	}
	return DocumentSchema.parse(await response.json());
}

export function documentQueryKey(id: string | null | undefined) {
	return ["documents", "detail", id ?? null] as const;
}

export function useDocument(id: string | null | undefined) {
	return useQuery({
		queryKey: documentQueryKey(id),
		queryFn: id ? () => fetchDocument(id) : skipToken,
		staleTime: Number.POSITIVE_INFINITY,
	});
}
