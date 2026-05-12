import { z } from "zod";

export const LayoutSearchSchema = z.object({
	documentId: z.string().min(1).optional(),
});

export type LayoutSearch = z.infer<typeof LayoutSearchSchema>;
