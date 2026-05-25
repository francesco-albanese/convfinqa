import asyncio
import json
import logging

from convfinqa.application.agent.tools import Tool
from convfinqa.application.agent.wire import safe_json_loads
from convfinqa.domain.ports.observability import ObservabilityPort
from convfinqa.logging import get_logger

TOOL_TIMEOUT_MATH_S = 0.1

logger = get_logger("convfinqa.send_message")


async def execute_tool(
    tool: Tool, raw_args: str, observability: ObservabilityPort
) -> tuple[str, bool]:
    args_dict = safe_json_loads(raw_args)
    async with observability.start_as_current_observation(
        as_type="tool", name=tool.name, input=args_dict
    ) as span:
        try:
            validated = tool.input_schema(**args_dict)
            loop = asyncio.get_running_loop()
            result_dict = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: tool.callable(**validated.model_dump())
                ),
                timeout=tool.timeout_s,
            )
            result_str = json.dumps(result_dict)
            span.set_output(result_str)
            return result_str, False
        except (ValueError, TypeError) as exc:
            error_str = json.dumps({"error": str(exc)})
            span.set_output(error_str)
            span.set_error()
            return error_str, True
        except TimeoutError:
            error_str = json.dumps({"error": "tool timeout"})
            span.set_output(error_str)
            span.set_error()
            return error_str, True
        except Exception as exc:  # noqa: BLE001
            logger.log(
                logging.WARNING,
                "tool_execution_error",
                extra={
                    "exc_type": exc.__class__.__name__,
                    "exc_message": str(exc) or exc.__class__.__name__,
                    "tool_name": tool.name,
                },
            )
            error_str = json.dumps({"error": "tool execution failed"})
            span.set_output(error_str)
            span.set_error()
            return error_str, True
