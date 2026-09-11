from fastmcp import FastMCP

from medication_tool import lookup_medicine
from interaction_tool import check_interaction
from escalation_tool import escalate_case


# Create the MCP server
mcp = FastMCP("DoseCheck Tools")


# Tool 1: Medicine lookup
@mcp.tool()
def medicine_lookup(medicine_name: str):
    """
    Look up a medicine in the demo medicine database.
    """
    return lookup_medicine(medicine_name)


# Tool 2: Medication interaction check
@mcp.tool()
def medication_interaction_check(drug_a: str, drug_b: str):
    """
    Check two medicines for a potential interaction.
    """
    return check_interaction(drug_a, drug_b)


# Tool 3: Escalate a case
@mcp.tool()
def escalate_to_professional(reason: str, context: dict):
    """
    Escalate an uncertain or high-risk case for professional review.
    """
    return escalate_case(reason, context)


# Start the MCP server
if __name__ == "__main__":
    mcp.run()