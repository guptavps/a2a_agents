import logging

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="[MCP] %(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("loan_closure_mcp")

mcp = FastMCP("mcps")

@mcp.tool()
def close_loan(loan_app_id: str) -> dict:
    """
    This tool helps to close a loan given its application ID.
    Args:
        loan_app_id (str): The ID of the loan application to be closed.

    Returns:
        dict: A dictionary containing the status and message of the loan closure operation.
    """
    logger.info("close_loan called for loan_app_id=%s", loan_app_id)
    if loan_app_id:
        response = {
            "structured_content": {
                "status": "success",
                "message": f"Loan with ID {loan_app_id} has been successfully closed."
            }
        }
    else:
        response = {
            "structured_content": {
                "status": "failure",
                "message": "Invalid loan application ID."
            }
        }
    logger.info("close_loan completed with status=%s", response["structured_content"]["status"])
    return response

if __name__ == "__main__":
    logger.info("Starting loan closure MCP server over stdio")
    mcp.run(transport="stdio")

