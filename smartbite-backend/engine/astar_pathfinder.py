"""
A* Pathfinding Algorithm for optimal route finding.
This finds the best road-based path between points considering various factors.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from models.location import Location, Coordinates
import heapq
import math


@dataclass
class PathNode:
    """Represents a node in the pathfinding grid."""
    coords: Coordinates
    g_cost: float = 0.0  # cost from start
    h_cost: float = 0.0  # heuristic cost to goal
    parent: Optional['PathNode'] = None
    
    @property
    def f_cost(self) -> float:
        """Total estimated cost."""
        return self.g_cost + self.h_cost
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __hash__(self):
        return hash(self.coords)
    
    def __eq__(self, other):
        if not isinstance(other, PathNode):
            return False
        return self.coords == other.coords


class AStarPathfinder:
    """
    A* pathfinding for finding optimal routes between stops.
    Uses a simplified grid-based model but can be extended with real road networks.
    """
    
    def __init__(self, grid_size: float = 1.0):
        self.grid_size = grid_size
        self.road_network: Dict[Coordinates, List[Coordinates]] = {}
    
    def heuristic(self, from_coord: Coordinates, to_coord: Coordinates) -> float:
        """Euclidean heuristic distance."""
        dx = to_coord.x - from_coord.x
        dy = to_coord.y - from_coord.y
        return math.sqrt(dx**2 + dy**2)
    
    def get_neighbors(self, coord: Coordinates) -> List[Coordinates]:
        """Get neighboring coordinates (8-directional movement)."""
        neighbors = []
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        for dx, dy in directions:
            new_coord = Coordinates(
                coord.x + dx * self.grid_size,
                coord.y + dy * self.grid_size
            )
            neighbors.append(new_coord)
        
        return neighbors
    
    def find_path(self, start: Coordinates, goal: Coordinates, 
                  max_iterations: int = 1000) -> List[Coordinates]:
        """
        Find optimal path from start to goal using A*.
        Returns list of coordinates representing the path.
        """
        open_set = []
        start_node = PathNode(start, g_cost=0.0)
        start_node.h_cost = self.heuristic(start, goal)
        
        heapq.heappush(open_set, start_node)
        
        closed_set: Dict[Coordinates, PathNode] = {}
        open_dict: Dict[Coordinates, PathNode] = {start: start_node}
        
        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_set)
            
            if current.coords == goal:
                # Reconstruct path
                path = []
                node = current
                while node:
                    path.append(node.coords)
                    node = node.parent
                return list(reversed(path))
            
            closed_set[current.coords] = current
            
            for neighbor_coord in self.get_neighbors(current.coords):
                if neighbor_coord in closed_set:
                    continue
                
                move_cost = self.heuristic(current.coords, neighbor_coord)
                g_cost = current.g_cost + move_cost
                
                if neighbor_coord in open_dict:
                    existing_node = open_dict[neighbor_coord]
                    if g_cost < existing_node.g_cost:
                        existing_node.g_cost = g_cost
                        existing_node.parent = current
                        existing_node.h_cost = self.heuristic(neighbor_coord, goal)
                else:
                    neighbor_node = PathNode(neighbor_coord, g_cost=g_cost)
                    neighbor_node.h_cost = self.heuristic(neighbor_coord, goal)
                    neighbor_node.parent = current
                    open_dict[neighbor_coord] = neighbor_node
                    heapq.heappush(open_set, neighbor_node)
        
        # If no path found, return direct path
        return [start, goal]
    
    def estimate_travel_distance(self, path: List[Coordinates]) -> float:
        """Estimate total travel distance from a path."""
        total = 0.0
        for i in range(len(path) - 1):
            dx = path[i+1].x - path[i].x
            dy = path[i+1].y - path[i].y
            total += math.sqrt(dx**2 + dy**2)
        return total
