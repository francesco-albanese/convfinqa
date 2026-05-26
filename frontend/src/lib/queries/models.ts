import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { apiFetch } from "@/lib/api/client";

export const ModelsResponseSchema = z.object({
	models: z.array(z.string()),
	default: z.string(),
});

export type ModelsResponse = z.infer<typeof ModelsResponseSchema>;

const MODELS_PATH = "/api/v1/models";

export async function fetchModels(): Promise<ModelsResponse> {
	const response = await apiFetch(MODELS_PATH, {
		headers: { Accept: "application/json" },
	});
	if (!response.ok) {
		throw new Error(`fetchModels: ${response.status} ${response.statusText}`);
	}
	return ModelsResponseSchema.parse(await response.json());
}

export function modelsQueryKey() {
	return ["models"] as const;
}

export function useModels() {
	return useQuery({
		queryKey: modelsQueryKey(),
		queryFn: fetchModels,
		staleTime: Number.POSITIVE_INFINITY,
	});
}
