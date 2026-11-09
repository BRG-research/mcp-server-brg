import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from brg_mcp.catalog import Catalog


def register(server: FastMCP, catalog: Catalog | None = None) -> None:
    @server.prompt()
    def fd(question: str = "") -> str:
        """Ask any question about form finding, force density method (Schek 1974, Linkwitz), and compas_fd.

        question: your question or problem formulation about form finding or force density.
        """
        ff_context = ""
        if catalog is not None:
            try:
                ff_context = catalog.read("form-finding-compas-fd")
            except Exception:
                pass

        header = (
            "You are an expert on Form Finding and Structural Equilibrium from the Block Research Group (BRG).\n"
            "The user is asking a question specifically about Form Finding and the Force Density Method.\n\n"
        )
        if question.strip():
            header += f"User Question: {question.strip()}\n\n"
        else:
            header += "Please ask the user for their form finding question or guide them through the method.\n\n"

        instructions = (
            "Guidance:\n"
            "1. Answer directly, mathematically, and clearly.\n"
            "2. Ground your answer in the classical Linear Force Density Method (Schek 1974):\n"
            "   - Coordinate vectors: x, y, z in R^n\n"
            "   - Branch-node incidence matrix: C in R^(m x n)\n"
            "   - Coordinate difference vectors: u = C x, v = C y, w = C z\n"
            "   - Branch forces s, branch lengths l, force densities q_i = s_i / l_i\n"
            "   - Diagonal force density matrix: Q = diag(q)\n"
            "   - Branch forces: s = Q l\n"
            "   - Nodal equilibrium system: C^T Q C x = p_x (or D x = p_x where D = C^T Q C)\n"
            "   - Partitioning into free nodes (f) and fixed support nodes (x):\n"
            "     D_f x_f + D_x x_x = p_xf  =>  D_f x_f = p_xf - D_x x_x\n"
            "     Solving for free nodes: x_f = D_f^(-1) (p_xf - D_x x_x)\n"
            "3. If relevant, reference Linkwitz (§ 6.2.1 - § 6.5) or compas_fd / compas_dr.\n"
            "4. Format formulas using standard LaTeX math and provide concise Python / NumPy examples when applicable.\n"
        )

        if ff_context:
            return header + instructions + "\n---\nReference Knowledge (BRG Form Finding):\n\n" + ff_context[:6000]
        return header + instructions
