# Wave Search in Maze

A Python desktop application demonstrating **one-directional wave search** in a maze using different movement operators.

The maze is generated automatically, but can also be edited manually.

## Features

* Generate mazes with configurable size, wall density and seed.
* Select the start and target vertices.
* Add and remove walls manually.
* Choose cross, diagonal or combined movement.
* Visualize the wave propagation step by step.
* Display the found shortest path and search statistics.
* Compare all movement operators under the same conditions.
* Run the search with or without animation.

## Wave Search

* Explores the maze level by level, marking each reachable cell with its distance from the start.
* Uses wave propagation to find the shortest path in an unweighted graph.
* Reconstructs the path by following cells with decreasing wave values.

## Technologies

* Python 3
* Tkinter
* `time`

## Running

```bash
python3 wave_search.py
```
