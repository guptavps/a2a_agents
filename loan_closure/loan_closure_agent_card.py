import os

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill


class LoanClosureAgentCard:
	DEFAULT_PORT = 8090
	PORT_ENV_VAR = "LOAN_CLOSURE_AGENT_PORT"
	URL_ENV_VAR = "LOAN_CLOSURE_AGENT_URL"

	def __init__(self, port: int | None = None) -> None:
		self.port = port if port is not None else int(
			os.getenv(self.PORT_ENV_VAR, str(self.DEFAULT_PORT))
		)
		self.url = os.getenv(self.URL_ENV_VAR, f"http://localhost:{self.port}")

	def get_agent_card(self) -> AgentCard:
		return AgentCard(
			name="loan_closure_agent",
			description=(
				"A loan servicing agent that processes loan closure requests, "
				"confirms the closure status, and reports the result to the requester."
			),
			supported_interfaces=[
				AgentInterface(
					url=self.url,
					protocol_binding="HTTP+JSON",
					protocol_version="1.0",
				)
			],
			version="1.0.0",
			capabilities=AgentCapabilities(),
			default_input_modes=["text/plain"],
			default_output_modes=["text/plain"],
			skills=[
				AgentSkill(
					id="close_loan",
					name="Close a loan",
					description=(
						"Closes a loan identified by its loan application ID and "
						"reports whether the closure succeeded."
					),
					tags=["loan servicing", "loan closure"],
					examples=[
						"Close loan application LOAN-12345.",
						"What is the closure status for loan application LOAN-12345?",
					],
					input_modes=["text/plain"],
					output_modes=["text/plain"],
				)
			],
		)
