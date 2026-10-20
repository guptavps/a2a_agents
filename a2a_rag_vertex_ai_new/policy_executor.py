import uuid

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, Task, TaskState, TaskStatus
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from policy_agent import build_policy_agent
from pipeline_config import PipelineConfig


_tracer = trace.get_tracer(__name__)


class PolicyExecutor(AgentExecutor):
    def __init__(self, config: PipelineConfig) -> None:
        self._runner = Runner(
            app_name="loan_policy_vertex_rag",
            agent=build_policy_agent(config),
            session_service=InMemorySessionService(),
            auto_create_session=True,
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        with _tracer.start_as_current_span("a2a.task.execute") as span:
            span.set_attribute("a2a.task.id", context.task_id)
            span.set_attribute("a2a.context.id", context.context_id)
            try:
                await self._execute_task(context, event_queue)
            except Exception as exc:
                span.set_attribute("error.type", type(exc).__name__)
                span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
                raise
            span.set_status(Status(StatusCode.OK))

    async def _execute_task(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await event_queue.enqueue_event(
            Task(
                id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
            )
        )
        await updater.start_work()
        response_text = ""
        async for event in self._runner.run_async(
            user_id="a2a-user",
            session_id=context.context_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=context.get_user_input())],
            ),
            invocation_id=str(uuid.uuid4()),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = "".join(
                    part.text or "" for part in event.content.parts if part.text
                )
        if not response_text:
            response_text = "The policy search did not return an answer."
        await updater.add_artifact([Part(text=response_text)], name="loan_policy_answer")
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()
