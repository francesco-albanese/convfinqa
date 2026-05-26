import { z } from "zod";

export const ConversationDataSchema = z.object({
	conversationId: z.string().min(1),
});

export const CitationDataSchema = z.object({
	rowLabel: z.string(),
	colLabel: z.string(),
});

export const TitleDataSchema = z.object({
	conversationId: z.string().min(1),
	title: z.string().min(1),
});

export const ChatDataPartSchema = z.object({
	type: z.string(),
	data: z.unknown().optional(),
});

export const AppSearchSchema = z.object({
	chatId: z.string().min(1).optional(),
	documentId: z.string().min(1).optional(),
});

export type AppSearch = z.infer<typeof AppSearchSchema>;
export type CitationData = z.infer<typeof CitationDataSchema>;
export type TitleData = z.infer<typeof TitleDataSchema>;
