import { Slider as SliderPrimitive } from "radix-ui";
import type * as React from "react";
import { cn } from "@/lib/utils";

function Slider({
	className,
	...props
}: React.ComponentProps<typeof SliderPrimitive.Root>) {
	const thumbCount = Array.isArray(props.value)
		? props.value.length
		: Array.isArray(props.defaultValue)
			? props.defaultValue.length
			: 1;

	return (
		<SliderPrimitive.Root
			data-slot="slider"
			className={cn(
				"relative flex w-full touch-none select-none items-center",
				className,
			)}
			{...props}
		>
			<SliderPrimitive.Track
				data-slot="slider-track"
				className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-secondary"
			>
				<SliderPrimitive.Range
					data-slot="slider-range"
					className="absolute h-full bg-primary"
				/>
			</SliderPrimitive.Track>
			{Array.from({ length: thumbCount }).map((_, index) => (
				<SliderPrimitive.Thumb
					// biome-ignore lint/suspicious/noArrayIndexKey: radix slider thumb count is fixed by the value/defaultValue length
					key={index}
					data-slot="slider-thumb"
					className="block h-4 w-4 rounded-full border border-primary bg-background shadow transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-50"
				/>
			))}
		</SliderPrimitive.Root>
	);
}

export { Slider };
