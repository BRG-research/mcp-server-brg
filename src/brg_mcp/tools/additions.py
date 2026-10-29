"""Course additions: a few lines added to the notebook the student has open, instead of a new notebook.

An addition returns three parts and the CAS website places them in the open notebook:
  imports  lines merged into the notebook's imports cell (only the names it is missing)
  code     a new cell below the student's cursor
  scene    lines added before the notebook's viewer.show(); a notebook without one gets `viewer` and a
           viewer.show() after the scene lines
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def primitives_add() -> dict:
    """A sphere, a point, a line and a polyline, added to the open notebook and its scene."""
    return {
        "name": "primitives",
        "imports": ["from compas.geometry import Line, Point, Polyline, Sphere",
                    "from compas_notebook import Viewer"],
        "code": "sphere = Sphere(1.5, point=[4, 0, 1.5])\n"
                "point = Point(7, 0, 0)\n"
                "line = Line([9, 0, 0], [9, 0, 3])\n"
                "polyline = Polyline([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 1]])",
        "scene": ["viewer.scene.add(sphere.to_mesh(u=32, v=16))",
                  "viewer.scene.add(point)",
                  "viewer.scene.add(line)",
                  "viewer.scene.add(polyline)"],
        "viewer": "viewer = Viewer()",
    }


def register(server: FastMCP) -> None:
    @server.tool()
    def compas_primitives_add() -> dict:
        """Adds COMPAS primitives (a sphere, a point, a line and a polyline) to the notebook that is open.

        Returns imports, code and scene lines, not a notebook: the website merges the imports into the
        notebook's imports cell, puts the code in a new cell below the cursor and the scene lines before
        viewer.show().
        """
        return primitives_add()
