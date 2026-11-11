# Exercises

## Exercise 1: Forces

**Fixed nodes:**

- `p1` = (0, 0, 0)
- `p2` = (5, 0, 3)
- `p3` = (0, 7, 3)
- `p4` = (7, 5, 0)

**Unknown node:** `p0` = (x, y, z)

**Edges:**

| Edge | Nodes |
|------|-------|
| a    | (0, 1) |
| b    | (0, 2) |
| c    | (0, 3) |
| d    | (0, 4) |

**Forces:**

- a: 1 kN
- b: 1 kN
- c: 1 kN
- d: 1 kN
- gravity at `p0`: 5 kN

**Questions:**

1. Determine `p0`.
2. Calculate the sum of forces in node `p0`.
3. What do you observe?

---

## Exercise 2: Force Densities

**Fixed nodes:**

- `p1` = (0, 0, 0)
- `p2` = (5, 0, 3)
- `p3` = (0, 7, 3)
- `p4` = (7, 5, 0)

**Unknown node:** `p0` = (x, y, z)

**Edges:**

| Edge | Nodes |
|------|-------|
| a    | (0, 1) |
| b    | (0, 2) |
| c    | (0, 3) |
| d    | (0, 4) |

**Force densities:**

- a: 1 kN
- b: 1 kN
- c: 1 kN
- d: 1 kN
- gravity at `p0`: 5 kN

**Questions:**

1. What is the sum of forces in node `p0`?
2. What happens if the force density is `q = 2` in bars b and d?

---

## Exercise 3: Grid Matrix

For the following net:

```
┌───┬───┬───┬───┬───┬───┐
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
└───┴───┴───┴───┴───┴───┘
```

**Build:**

1. A branch-node matrix for the standard example grid.
2. A vector of force densities `q`.
3. A vector of coordinates `x`, `y`, `z`.

---

## Exercise 4: Grid Variations

For the following net:

```
┌───┬───┬───┬───┬───┬───┐
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │
└───┴───┴───┴───┴───┴───┘
```

**Vary:**

1. The boundary conditions in the z-axis.
2. The force densities `q`.
3. The external loads `p`.
