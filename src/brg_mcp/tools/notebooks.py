"""Course notebook tools: runnable JupyterLite notebooks for the CAS website, built like the course's own.

A tool returns notebook cells; the client writes them into a notebook (the website's BRG terminal opens
them in JupyterLite with its notebook tool). The cells follow the course conventions of
knowledge/02_computational_design: pinned installs, imports, short headings, a COMPAS scene at the end.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

# The same pins as the course notebooks, so a generated notebook runs in the website's JupyterLite.
INSTALL = ("%pip install -q compas==2.15.1 pythreejs==2.4.2\n"
           "%pip install -q compas_notebook==0.11.0 --no-deps")
BOX_NAME = "brg_mcp"


def box_notebook(xsize: float = 2.0, ysize: float = 1.0, zsize: float = 1.5, color: str = "#5552bb") -> dict:
    """The cells of a notebook with one COMPAS box named brg_mcp, its mesh and a scene."""
    if min(xsize, ysize, zsize) <= 0:
        raise ValueError("the box sizes must be positive")
    if not (len(color) == 7 and color[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in color[1:])):
        raise ValueError('color must be a hex colour such as "#5552bb"')
    cells = [
        {"type": "markdown", "source": f"# A COMPAS box: {BOX_NAME}"},
        {"type": "code", "source": INSTALL},
        {"type": "code", "source": "from compas.geometry import Box\n"
                                   "from compas_notebook import Viewer\n"
                                   "from compas_notebook.config import Config"},
        {"type": "markdown", "source": "## Box and mesh"},
        {"type": "code", "source": f"box = Box({xsize!r}, {ysize!r}, {zsize!r})\n"
                                   f'box.name = "{BOX_NAME}"\n'
                                   "mesh = box.to_mesh()\n"
                                   "box.name, box.volume, box.area"},
        {"type": "markdown", "source": "## Scene"},
        {"type": "code", "source": "config = Config()\n"
                                   "config.view.width, config.view.height = 700, 360\n"
                                   "config.view.camera.position = [4, -6, 3]\n"
                                   "viewer = Viewer(config=config)\n"
                                   f'viewer.scene.add(mesh, name=box.name, color="{color}", show_vertices=True, show_edges=True)\n'
                                   "viewer.show()"},
    ]
    return {"name": BOX_NAME, "file": f"{BOX_NAME}.ipynb", "cells": cells}


def register(server: FastMCP) -> None:
    @server.tool()
    def compas_box_notebook(xsize: float = 2.0, ysize: float = 1.0, zsize: float = 1.5,
                            color: str = "#5552bb") -> dict:
        """A runnable course notebook that creates one COMPAS box named "brg_mcp" and shows it in a scene.

        Call it when the user asks to create a box in the notebook. xsize, ysize, zsize: the box's sizes
        (default 2 × 1 × 1.5); color: a hex colour. Returns the notebook's file name and its cells; pass them
        unchanged to the notebook tool, which writes and opens the notebook for the user to run.
        """
        return box_notebook(xsize, ysize, zsize, color)
