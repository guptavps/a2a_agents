from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskStatus,Message, Part, Role, TaskState
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
import loan_closure_agent
from google.genai import types
from a2a.utils.errors import TaskNotCancelableError
from a2a.server.events import EventQueue

class LoanClosureExecutor(AgentExecutor):
    def __init__(self) -> None:
        """ Initialization of the LoanClosureExecutor. """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """ Execute the loan closure process. """
        task = context.current_task
        task_id = context.task_id
        context_id = context.context_id
        if not task_id or not context_id:
            raise RuntimeError("Task ID or Context ID is missing.")

        if task is None:
            await event_queue.enqueue_event(Task(
                id=task_id, 
                context_id=context_id, 
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED)))
        updater = TaskUpdater(event_queue, task_id, context_id)
        query=context.get_user_input()
        await updater.update_status(TaskState.TASK_STATE_WORKING, 
                                    Message(role=Role.ROLE_AGENT, 
                                            parts=[Part(text="Processing loan closure request")],
                                            task_id=task_id,
                                            context_id=context_id))
        response_text = await self.execute_loan_closure_agent(query)
        await updater.add_artifact([Part(text=response_text)], name="Loan closure response")
        await updater.complete(Message(role=Role.ROLE_AGENT, 
                                      parts=[Part(text=response_text)],
                                      task_id=task_id,
                                      context_id=context_id))


    async def execute_loan_closure_agent(self, user_input: str):
        session_service = InMemorySessionService()
        runner = Runner(agent=loan_closure_agent.loan_closure_agent,
                        app_name=loan_closure_agent.APP_NAME,
                        session_service=session_service
                        )
        session = await session_service.create_session(app_name=loan_closure_agent.APP_NAME,
                                                        user_id=loan_closure_agent.USER_ID)
        new_message = types.Content(role="user", parts=[types.Part(text=user_input)])
        response_text=""
        async for event in runner.run_async(
            user_id=loan_closure_agent.USER_ID, session_id=session.id, new_message=new_message):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "function_call", None):
                        fc=part.function_call
                        print(f"Function call detected: {fc.name} args={fc.args}")
                    if getattr(part, "function_response", None):
                        fr=part.function_response
                        print(f"Tool response detected: {fr.name} response={fr.response}")
                    if getattr(part, "text", None):
                        response_text += part.text
        print("execute_loan_closure_agent", response_text)
        return response_text

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise TaskNotCancelableError()
