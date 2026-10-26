# Computational Structural Design with COMPAS

These are the canonical BRG course notebooks for Chapter 2: mathematical and
geometrical foundations, primitives, data, exchange, geometry, data structures,
AEC models and IFC, matrix decomposition, and optimisation. Start with one box.
Introduce one new concept at a time before combining concepts in optional
structural examples. No prior Python knowledge is assumed.

The editable sources live in [`notebooks/`](notebooks/), with order and website
metadata in [`tutorials.json`](tutorials.json). Files served by the BRG Teaching
website are published copies. This course does not depend on an external notebook
repository at runtime. Notebooks are grouped by topic in `notebooks/<topic>/` and
follow manifest order. Each is deliberately minimal: a title, short section
headings and runnable code that ends in a COMPAS scene. There are no assertions,
print statements or written exercises; cells display results as their last
expression. Explanations and tasks are given in class.

## Sequence and purpose

| Order | Notebook | Why it is needed | Guided estimate |
| --- | --- | --- | --- |
| 1 | [A COMPAS box](notebooks/01-basics/01-box.ipynb) | Turn dimensions into an inspectable primitive and scene. | 30 min |
| 2 | [Data basics](notebooks/01-basics/02-data.ipynb) | Distinguish Python values, metadata and object properties. | 30 min |
| 3 | [COMPAS JSON](notebooks/01-basics/03-json.ipynb) | Preserve a box, point and units beyond one Python session. | 45 min |
| 4 | [Vectors and frames](notebooks/02-geometry/01-vectors-frames.ipynb) | Measure alignment and place geometry in local coordinates. | 60 min |
| 5 | [Parametric patterns](notebooks/02-geometry/02-brick-pattern.ipynb) | Generate a grid and a small brick wall with loops and a rule. | 75 min |
| 6 | [A graph](notebooks/03-datastructures/01-graph.ipynb) | Separate connectivity and attributes from node positions. | 45 min |
| 7 | [A mesh](notebooks/03-datastructures/02-mesh.ipynb) | Add face cycles, normals and an indexed connectivity matrix. | 60 min |
| 8 | [A COMPAS model](notebooks/04-aec/01-model.ipynb) | Organise one named element inside a group and save that hierarchy. | 35 min |
| 9 | [An IFC wall](notebooks/04-aec/02-ifc.ipynb) | Export identity, units, storey and shape representation. | 45 min |
| 10 | [Matrix decomposition](notebooks/05-solvers/01-qr.ipynb) | Locate a point from two constraints using QR and a residual check. | 60 min |
| 11 | [Constrained optimisation](notebooks/05-solvers/02-optimisation.ipynb) | Search for dimensions satisfying volume and height requirements. | 90 min |
| Extension | [Truss equilibrium](notebooks/06-structures/01-truss.ipynb) | Combine a graph and QR to balance axial forces and reactions. | 90 min |
| Extension | [Force-density cable](notebooks/06-structures/02-cable.ipynb) | Bridge to Chapter 4: equilibrium geometry for prescribed force density. | 45 min |

The guided estimates total **9 h 35 min for foundations**, plus **2 h 15 min of
optional extensions**. They are activities within a 30-hour course, not a claim
that notebook code alone supplies 30 hours of instruction. A suggested five-session
plan allocates six hours each to: (1) primitives, Python data and exchange;
(2) geometry and algorithms; (3) graphs, meshes, models and IFC;
(4) matrix methods and optimisation; (5) a supervised parameter-study project,
discussion and review. Use the remaining time for explanations, independent
exercises, debugging, feedback and presentations. Select extensions to suit the
class after the foundations.

## Running and saving

Open a notebook in the BRG browser workspace or desktop Jupyter with a Python 3
kernel. Run cells in order with **Shift+Enter**, or choose **Run → Run All Cells**.
Setup cells install `compas==2.15.1`, `pythreejs==2.4.2` and
`compas_notebook==0.11.0 --no-deps`. Only the cable adds `compas_fd==0.5.4`;
only the model adds `compas_model==0.9.3`. Desktop environments also need NumPy
and SciPy; install with `%pip install -q numpy scipy` if absent. Lessons use
native COMPAS objects and `viewer.scene.add(...); viewer.show()`.

The BRG browser runtime pins **Pyodide 0.29.3 / Python 3.13.2**, which provides
NumPy 2.2.5, SciPy 1.14.1 and Shapely 2.0.7. Keep the supplied browser packages
rather than requesting recent desktop binary wheels. The IFC notebook selects
the official IfcOpenShell 0.8.4 `cp313 / pyodide_2025_0 / wasm32` wheel in browser
Python, and `ifcopenshell==0.8.4` on desktop. Its COMPAS picture is a separate
preview driven by the same dimensions; it is not extracted from the IFC geometry.

Save with **Ctrl+S** or **⌘S**, then download your work through
**File → Save and Export Notebook As → Notebook**. Download generated JSON and
IFC files from Jupyter's file browser too. Browser storage belongs to that browser
and machine. Source notebooks have empty outputs and execution counts; exported
student copies can retain results and scenes.

## Publishing the course sources

From this repository's root:

```bash
python3 knowledge/02_computational_design/publish_notebooks.py \
  --website /home/pv/brg/code_teaching/Teaching/CAS/website
python3 knowledge/02_computational_design/publish_notebooks.py \
  --website /home/pv/brg/code_teaching/Teaching/CAS/website --check
```

The publisher validates the manifest, copies declared notebooks and generates
the website registry. `--check` compares without writing. This prepares website
files; deployment is handled by the Teaching repository.

## Pedagogic provenance

These are BRG course adaptations and original exercises, not copied workshop
bundles. The first box and five-node/four-edge/two-support cable retain the existing
CAS starting examples. Seoul 2025 provides the closest foundation-level progression;
older Python and topology materials remain useful for beginners. The newest
workshop is not automatically the best starting point: CGS 2026 centres on graphic
statics and Grasshopper, which belong later in the course.

The following are repository commit timestamps verified during the source review
on 2026-10-20, not claimed event dates. Links fix the reviewed revision.

| Primary source | Reviewed commit date (UTC) | Use in this course |
| --- | --- | --- |
| [BRG Seoul 2025, COMPAS foundations](https://github.com/BRG-teaching/seoul_2025/tree/b641b732a3e337eb3a19d7a91048946820695e7a/05_compas) | 2025-07-09 17:43:38 | Minimal Box, Frame, geometry, mesh and JSON progression. |
| [BRG Calgary 2025](https://github.com/BRG-teaching/Calgary2025/tree/05cb4f76aa7ff43a113f0f6ff494970d5c7756c4) | 2025-02-11 23:49:06 | Introductory objects and algorithmic geometry. |
| [BRG UCL 2024](https://github.com/BRG-teaching/UCL_2024/tree/6bec117f799e59be39529aa2bd6f3aa203d4ba4d) | 2024-07-11 14:09:43 | Data exchange and model context. |
| [BRG CSD2 2022](https://github.com/BRG-teaching/CSD2_2022/tree/8c9b0fe9ad26e154714e3af7d93bed45ed090b7a) | 2023-02-16 14:52:27 | Gradual Python notebook pedagogy. |
| [COMPAS ITA21](https://github.com/compas-teaching/ITA21/tree/7213b322067efe6102e998e83194e8dbe39a82bf) | 2021-11-17 09:24:32 | Vectors, frames and topology foundations. |
| [BRG CGS 2026](https://github.com/BRG-teaching/CGS-2026/tree/c6019554236f773b4426ceb6ba4127a73c516097) | 2026-10-15 15:07:06 | Recent graphic-statics context, not the beginner template. |
| [COMPAS JupyterLite](https://github.com/compas-dev/compas-jupyterlite/tree/d9df5aef10685c80507236554900d72b86504d6a) | 2025-03-13 12:58:04 | Browser installation and native viewer pattern. |
| [COMPAS Notebook](https://github.com/compas-dev/compas_notebook/tree/cdeda9c50ab1c13432fb186599a77789a8dc395e) | 2025-12-10 14:30:37 | Viewer implementation reference. |

Notebooks link the relevant [COMPAS 2.15.1 APIs](https://compas.dev/compas/2.15.1/api/),
[NumPy linear algebra](https://numpy.org/doc/stable/reference/routines.linalg.html),
[SciPy optimisation](https://docs.scipy.org/doc/scipy/reference/optimize.html), and
[IfcOpenShell browser installation](https://docs.ifcopenshell.org/ifcopenshell-python/installation.html#web-assembly).
Rhino scene drawing and native CAD plugins from the workshops are replaced by
the notebook viewer. JSON and COMPAS Model are distinguished explicitly from IFC.
Autodifferentiation is introduced as a later extension; the optimisation lesson
supplies and independently checks analytic gradients.

## Checks and reference results

The minimal rewrite (2026-10-26) was executed in a fresh desktop Python 3.13
kernel with the pinned packages; every cell ran and the displayed values match the
reference results below. Repeat browser checks in JupyterLite when changing runtime
dependencies; desktop execution alone does not verify rendering. Rebuild dependent
objects by rerunning in order. The truss is a static force solve, the cable is force-density
form-finding, and the optimisation example is a geometric enclosure problem.

Reference results: box volume **3 m³**, area **13 m²**; line intersection **(2, 1) m**;
truss forces **−7.071068, −7.071068, +5 kN**, with **5 kN** vertical reactions;
cable free heights **−0.75, −1, −0.75 m**; optimum enclosure dimensions
**(√3, √3, 1) m**, area **6 + 4√3 m²**. In the force-density solver, physical support
reactions are the negatives of the fixed-node residuals.
