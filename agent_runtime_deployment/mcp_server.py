import logging

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="[MCP] %(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("loan_closure_mcp")
mcp = FastMCP("loan_closure_mcp")


@mcp.tool()
def close_loan(loan_app_id: str) -> dict:
    """Close the specified loan and return a structured JSON result."""
    logger.info("close_loan called for loan_app_id=%s", loan_app_id)
    if not loan_app_id:
        result = {"status": "failure", "message": "Invalid loan application ID."}
    else:
        result = {
            "status": "success",
            "message": f"Loan with ID {loan_app_id} has been successfully closed.",
        }
    logger.info("close_loan completed with status=%s", result["status"])
    return {"structured_content": result}


if __name__ == "__main__":
    logger.info("Starting loan closure MCP server over stdio")
    mcp.run(transport="stdio")
