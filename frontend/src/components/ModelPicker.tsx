import { useId } from "react";
import { useModels } from "@/lib/queries/models";
import { setSelectedModel, useSelectedModel } from "@/lib/ui/modelStore";
import { cn } from "@/lib/utils";

export function ModelPicker() {
	const labelId = useId();
	const { data } = useModels();
	const selected = useSelectedModel();

	if (!data || data.models.length === 0) return null;

	const value = selected ?? data.default;

	return (
		<div className="flex items-center gap-2">
			<label
				id={labelId}
				className="text-muted-foreground text-xs"
				htmlFor={labelId}
			>
				Model
			</label>
			<select
				aria-labelledby={labelId}
				value={value}
				onChange={(event) => setSelectedModel(event.target.value)}
				className={cn(
					"rounded-md border border-border bg-background px-2 py-1 text-foreground text-xs",
					"focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
				)}
			>
				{data.models.map((model) => (
					<option key={model} value={model}>
						{model}
					</option>
				))}
			</select>
		</div>
	);
}
