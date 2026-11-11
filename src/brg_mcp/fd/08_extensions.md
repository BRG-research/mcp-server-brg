# Extensions of the Force Density Method from Working Open Source Code

The standard Force Density Method solves one linear system per coordinate axis when the force densities $q$, the fixed support coordinates $x_F, y_F, z_F$, and the nodal loads $p_x, p_y, p_z$ are prescribed:

$$
\left(C_N^{T}\,Q\,C_N\right) x_N = p_x - C_N^{T}\,Q\,C_F\,x_F
$$

Open source form finding libraries extend this core matrix equation with geometric support constraints, live tributary and follower loads, compression and tensegrity self stress, minimal surface weights, analytical sensitivity Jacobians for goal optimisation, and nonlinear elastic or wrinkling material laws. Below are the working GitHub repositories and the exact solver modules that inspire our local extension notebooks.

---

## 1. Geometric Support Constraints, Per Axis Rollers, and Live Tributary Selfweight

Instead of locking every support to a fixed point in space, constrained solvers allow supports to slide frictionlessly along lines, circles, curves, planes, and freeform surfaces while updating tributary surface selfweight at each iteration.

### Working Code Repositories

* **BlockResearchGroup/compas_fd**: https://github.com/BlockResearchGroup/compas_fd
  * `src/compas_fd/solvers/fd_numpy.py`: single step sparse solve plus full nodal residual and support reaction array `residuals = p - A.dot(xyz)`.
  * `src/compas_fd/solvers/fd_constrained_numpy.py`: damped outer loop (`fd_constrained_numpy`) that solves `Ai * xyz[free] = p[free] - Af * xyz[fixed]`, evaluates residuals at constrained supports, projects each residual onto the local tangent space of its constraint geometry, updates `location + damping * tangent`, and reprojects onto the geometry until `max(norm(tangent_residuals)) < tol_res`.
  * `src/compas_fd/constraints/`: `LineConstraint` (`lineconstraint.py`), `PlaneConstraint` (`planeconstraint.py`), `CircleConstraint` (`circleconstraint.py`), `CurveConstraint` (`curveconstraint.py`), `SurfaceConstraint` (`surfaceconstraint.py`), `VectorConstraint` (`vectorconstraint.py`), and `FrameConstraint` (`frameconstraint.py`).
  * `src/compas_fd/loads/selfweight.py`: `SelfweightCalculator` computes face centroids via a normalised face matrix $F\,x$, splits every quad into sub triangles of area $\frac{1}{4}\|(x_j - x_i)\times(c_f - x_i)\|$, and multiplies tributary area by thickness and density inside each solver iteration.
* **keithjlee/Asap.jl**: https://github.com/keithjlee/Asap.jl
  * `src/FDM/Analysis/solving.jl` and `analysis.jl`: exploits coordinate separability by building independent free and fixed partitions (`AxisSystem`) per coordinate axis $(x, y, z)$, solving axis aligned roller and planar supports in one linear pass without iteration while caching symbolic sparse factorisations for fast $q$ updates.

### Local Notebook Implementation

* `extension_01_geometric_constraints.ipynb`: implements support reaction vectors $-r_F$, one shot per axis roller supports (`Asap.jl`), iterative tangential residual projection for tilted line rails, circular rings, and curved surfaces, and live quad tributary area selfweight (`compas_fd`).

---

## 2. Compression Gridshells and Mixed Sign Tensegrity Self Stress

Flipping $q < 0$ turns tension nets into inverted funicular compression shells, while combining tension cables ($q > 0$) and compression struts ($q < 0$) yields cable domes and free standing tensegrities governed by the nullspaces of the equilibrium matrix $A_{\text{eq}}$ and the stress matrix $D = C^{T}\,Q\,C$.

### Working Code Repositories

* **amandaghassaei/ShellFormFinding**: https://github.com/amandaghassaei/ShellFormFinding
  * `js/staticModel.js` and `js/dynamicModel.js`: interactive compression gridshell form finding with negative force densities, selfweight toggles, material assignment, and total load path tracking $\sum |f_k|\,l_k$.
* **sevamoo/Force_Density_Method**: https://github.com/sevamoo/Force_Density_Method
  * `fdmlib/fdm.py`: parametric network form finding (`solve_fdm_Sheck`) with mixed sign $q$ colouring ($q \ge 0$ tension, $q < 0$ compression) and `cal_loadpath`.
* **alexHaridis/ForceDensityAPI**: https://github.com/alexHaridis/ForceDensityAPI
  * `source/ForceDensityMethod.java`: explicit matrix assembly of $D_N, D_F, U, V, W, L$ and structural performance metric $\sigma_{FL} = f^{T}\,l$.
* **JonasFeron/Muscle**: https://github.com/JonasFeron/Muscle
  * `src/MusclePy/musclepy/solvers/svd/main.py` and `selfstress/modes.py`: Singular Value Decomposition of the $3n_{\text{dof}} \times m$ equilibrium matrix $A_{\text{eq}}$ to extract static indeterminacy $s$ (self stress modes converted to force densities via $q_s = L^{-1}\,v_s$), kinematic mechanisms $m$, and Gauss Jordan mode localisation respecting cable ($q \ge 0$) and strut ($q \le 0$) signs.
* **hermes98761234/tensegrity-designer**: https://github.com/hermes98761234/tensegrity-designer
  * `src/lib/formfinding.ts` and `stability.ts`: free standing tensegrity form finding (`forceDensityFormFind`) by alternating between the nullspace of $A_{\text{eq}}^{T}A_{\text{eq}}$ (`selfStress`) and projecting coordinates onto the 4 dimensional nullspace of the $n \times n$ stress matrix $D = C^{T}\,Q\,C$.

### Local Notebook Implementation

* `extension_02_compression_and_tensegrity.ipynb`: implements funicular compression gridshells ($q < 0$, stiffened perimeter arch ribs, load path $\sum |f_k|\,l_k$, fabrication cut lengths $l_0 > l$), anchored mixed cable strut domes ($D_N \succ 0$ check), and free standing tensegrity form finding via SVD self stress and stress matrix nullspace projection (`Muscle` and `tensegrity-designer`).

---

## 3. Cotangent Minimal Surfaces and Follower Pressure Loads

Uniform force densities $q_k = 1$ minimise mesh dependent Dirichlet energy $\frac{1}{2}\sum q_k\,l_k^2$ rather than surface area, and vertical loads cannot model internal pressure on curved cushions. Updating $q_k$ from opposite triangle cotangents yields true minimal surfaces, while updating $p(x)$ along local face normals yields pneumatic structures.

### Working Code Repositories

* **jikempff/Mite**: https://github.com/jikempff/Mite
  * `src/Mite.Core/FormFinding/ForceDensityMethod.cs`, `MinimalSurface.cs`, and `Geometry/DiscreteOperators.cs`: `MinimalSurface.Compute` freezes symmetric cotangent edge weights $q_k = \max\!\left(\tfrac{1}{2}(\cot\alpha_k + \cot\beta_k),\,10^{-4}\right)$ (`CotangentEdgeWeights`, computed directly as $(a \cdot b)/\|a \times b\|$), solves the sparse Laplace / FDM linear system, and updates weights for 15 to 20 outer iterations to reach minimal area without slow explicit Euler flow.
* **arpastrana/jax_fdm**: https://github.com/arpastrana/jax_fdm
  * `src/jax_fdm/equilibrium/loads.py` and `models.py`: `nodes_load_from_faces(..., is_local=True)` rotates face area loads from each polygon's local coordinate frame (`face_load_lcs`) into global coordinates and distributes tributary triangle forces to nodes inside the fixed point equilibrium loop `equilibrium_iterative_xyz` (`tmax > 1`).

### Local Notebook Implementation

* `extension_03_minimal_and_pneumatic_surfaces.ipynb`: compares uniform $q$ Dirichlet nets against iterative cotangent weighted minimal surfaces on a saddle patch and a two ring catenoid soap film (`Mite`), then implements follower face normal pressure ${\color{#2e9e4a} p_i(x)} = \sum_{t \ni i}\frac{1}{3}\,\pi\,\vec{s}_t$ for an inflated pneumatic cushion (`jax_fdm`).

---

## 4. Differentiable Sensitivity Jacobians, Goal Optimisation, and Quad Planarisation

Differentiating the linear FDM system with respect to $q$ (and support coordinates $x_F$) turns form finding into an inverse design layer where gradient based optimisers match target coordinates, equalise bar lengths or cable forces, minimise load path, or planarise quad gridshell panels while keeping every iterate in exact static equilibrium.

### Working Code Repositories

* **arpastrana/jax_fdm**: https://github.com/arpastrana/jax_fdm
  * `src/jax_fdm/equilibrium/models.py` and `solvers/`: forward and implicit differentiation through linear and iterative FDM (`constrained_fdm`).
  * `src/jax_fdm/goals/` and `parameters/`: modular goals including `VertexPointGoal`, `EdgeLengthGoal`, `EdgeForceGoal` (`examples/truss/truss_equal_force.py`), `NetworkLoadPathGoal` (`examples/arch/arch_loadpath.py`), and `MeshPlanarityGoal` (`examples/gridshell/gridshell_planarization.py`), paired with bounded design parameters (`EdgeForceDensityParameter`, `VertexSupportXParameter`).
* **arpastrana/dfdm**: https://github.com/arpastrana/dfdm
  * `src/dfdm/equilibrium/fdm.py` and `src/dfdm/goals/`: PyTorch differentiable FDM solver and node, edge, and network goal losses.
* **PrincetonLIPS/neural_fdm**: https://github.com/PrincetonLIPS/neural_fdm and **efradeca/vae-fdm**: https://github.com/efradeca/vae-fdm
  * `src/neural_fdm/models.py`, `losses.py`, and `classical.py`: sign preserving box bounds (`_build_bounds` for tension cables $q \in [q_{\min}, q_{\max}]$ and compression vaults $q \in [-q_{\max}, -q_{\min}]$) and neural / GNN encoders trained directly through the differentiable FDM equilibrium decoder.
* **jikempff/Mite**: https://github.com/jikempff/Mite
  * `src/Mite.Core/FormFinding/Planarization.cs` and `PlanarizationOptimizer.cs`: best fit face plane normal projection and deviation metrics for flat panel gridshell cladding.

### Local Notebook Implementation

* `extension_04_differentiable_goal_optimisation.ipynb`: derives and verifies the exact analytical Jacobians $\partial x_N / \partial q = -D_N^{-1}\,C_N^{T}\,U$, $\partial l / \partial q$, and $\partial f / \partial q = L + Q\,\partial l / \partial q$ in pure NumPy, then solves target shape + bar length equalisation with edge group tying, cable force equalisation (`truss_equal_force.py`), and compression gridshell quad planarisation (`gridshell_planarization.py`).

---

## 5. Material Driven Elastic Nets, Anisotropic Prestress, and Tension Only Wrinkling

Once bars or yarns are cut to unstretched rest lengths $l_{0,k}$ with axial stiffness $EA_k$, force densities are no longer constant under new external loads: $q_k(l_k) = f_k(l_k)/l_k$ becomes state dependent, with tension only cables or membranes going slack ($q_k = 0$) whenever $l_k \le l_{0,k}$.

### Working Code Repositories

* **damianbrenlla/form-finding**: https://github.com/damianbrenlla/form-finding
  * `python_core/solvers_ff.py`: `ForceDensitySolver` and `UnderwoodDRSolver` combine axial stiffness $EA / l_0$, directional warp and weft prestress (`prestress_warp_N_mm`, `prestress_weft_N_mm`), stiffened perimeter edge cables (`edge_cable_prestress_N`), and tension only membrane wrinkling cutoff (`axial_forces = np.maximum(0.0, E * area * strains + prestress)`).
* **JonasFeron/Muscle**: https://github.com/JonasFeron/Muscle
  * `src/Muscle/View/GH_BilinearMaterial.cs` and `src/MusclePy/musclepy/solvers/dm/nonlinear_dm.py`: bilinear axial material law with distinct tension and compression moduli ($E_t > 0, E_c = 0$ for slackening cables).

### Local Notebook Implementation

* `extension_05_elastic_and_wrinkling_nets.ipynb`: closes the loop with the presentation's unstretched length formula $l_{0,k} = EA_k\,l_k / (EA_k + f_k)$ by solving nonlinear elastic FDM updates $q_k(l_k) = \max(0,\,EA_k(l_k - l_{0,k})/(l_{0,k}\,l_k))$ under asymmetric patch loads, upward wind suction causing slack wrinkling zones, and anisotropic warp/weft textiles with stiff boundary edge cables (`form-finding` and `Muscle`).
