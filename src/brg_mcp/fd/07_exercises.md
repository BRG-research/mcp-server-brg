# Exercises

## Exercise 1 - Forces

Four fixed points:
- p1(0,0,0)
- p2(5,0,3)
- p3(0,7,3)
- p4(7,5,0)

Free unknown point:
- p0(x,y,z)

Edges
- a (0,1)
- b (0,2)
- c (0,3)
- d (0,4)

Forces:
- a 1 kN
- b 1 kN
- c 1 kN
- d 1 kN
- gravity at p0 = 5 kN

Question:
- Determine p0.
- Calculate the sum of forces in node p0.
- What do you observe?

## Exercise 2 - Force Densities

Four fixed points:
- p1(0,0,0)
- p2(5,0,3)
- p3(0,7,3)
- p4(7,5,0)

Free unknown point:
- p0(x,y,z)

Edges
- a (0,1)
- b (0,2)
- c (0,3)
- d (0,4)

Force densities:
- a 1 kN
- b 1 kN
- c 1 kN
- d 1 kN
- gravity at p0 = 5 kN

Question:
- What is the sum of forces in node p0?
- What happens if the force density q = 2 in bars b and d ?


## Exercise 3 - Grid Matrix

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


- a branch-node matrix for the standard example grid
- vector of force densities q
- vector of coordinates x, y, z

## Exercise 4 - Grid Variations

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

- change the boundary conditions in z-axis
- change force densities q
- change external loads p 