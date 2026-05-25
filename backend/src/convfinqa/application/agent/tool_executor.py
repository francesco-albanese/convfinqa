import asyncio
import json
import logging

from convfinqa.application.agent.tools import Tool
from convfinqa.logging import get_logger

TOOL_TIMEOUT_MATH_S = 0.1

logger = get_logger("convfinqa.send_message")


async def execute_tool(tool: Tool, raw_args: str) -> tuple[str, bool]:
    try:
        args_dict = json.loads(raw_args)
        validated = tool.input_schema(**args_dict)
        loop = asyncio.get_running_loop()
        result_dict = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: tool.callable(**validated.model_dump())),
            timeout=tool.timeout_s,
        )
        return json.dumps(result_dict), False
    except (ValueError, TypeError) as exc:
        return json.dumps({"error": str(exc)}), True
    except TimeoutError:
        return json.dumps({"error": "tool timeout"}), True
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
        return json.dumps({"error": "tool execution failed"}), True
