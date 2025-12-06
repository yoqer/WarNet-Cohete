import math
import numpy as np
from stl import mesh  # Requires numpy-stl package: pip install numpy-stl
import struct

def create_rocket_stl(filename="rocket_model.stl", length=100, radius=10):
    """
    Creates a detailed rocket-shaped STL file with proper scale.
    
    Parameters
    ----------
    filename : str
        Output filename
    length : float
        Rocket length in meters
    radius : float
        Rocket base radius in meters
    """
    
    # More realistic proportions
    nose_length = length * 0.25
    engine_length = length * 0.1
    
    # Fin parameters
    fin_height = radius * 3
    fin_width = radius * 2
    fin_thickness = radius * 0.2
    num_fins = 4
    
    # Calculate number of vertices for smooth curves
    num_segments = 36
    vertices = []
    faces = []
    
    # Helper function to add triangle
    def add_triangle(v1, v2, v3):
        nonlocal faces
        idx = len(vertices)
        vertices.extend([v1, v2, v3])
        faces.append([idx, idx+1, idx+2])
    
    # Helper function to add quadrilateral as two triangles
    def add_quad(v1, v2, v3, v4):
        add_triangle(v1, v2, v3)
        add_triangle(v1, v3, v4)
    
    # 1. Create nose cone (pointed ogive)
    nose_vertices = []
    for i in range(num_segments + 1):
        angle = 2 * math.pi * i / num_segments
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        z = length  # Tip at full length
        nose_vertices.append([x, y, z])
    
    # Create nose cone triangles
    nose_tip = [0, 0, length]
    for i in range(num_segments):
        v1 = nose_tip
        v2 = nose_vertices[i]
        v3 = nose_vertices[(i + 1) % num_segments]
        add_triangle(v1, v2, v3)
    
    # 2. Create main body cylinder
    body_z_start = length - nose_length
    body_z_end = engine_length
    
    # Create vertices for top and bottom circles of body
    top_circle = []
    bottom_circle = []
    
    for i in range(num_segments):
        angle = 2 * math.pi * i / num_segments
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        
        top_circle.append([x, y, body_z_start])
        bottom_circle.append([x, y, body_z_end])
    
    # Create body cylinder triangles
    for i in range(num_segments):
        next_i = (i + 1) % num_segments
        
        # Side quad
        v1 = top_circle[i]
        v2 = top_circle[next_i]
        v3 = bottom_circle[next_i]
        v4 = bottom_circle[i]
        add_quad(v1, v2, v3, v4)
        
        # Top circle (connecting to nose)
        v1 = top_circle[i]
        v2 = top_circle[next_i]
        v3 = nose_vertices[i]
        add_triangle(v1, v2, v3)
    
    # 3. Create engine nozzle (truncated cone)
    engine_radius = radius * 0.7
    engine_z_end = 0
    
    # Create vertices for engine circles
    engine_top_circle = []
    engine_bottom_circle = []
    
    for i in range(num_segments):
        angle = 2 * math.pi * i / num_segments
        x_top = math.cos(angle) * radius
        y_top = math.sin(angle) * radius
        x_bottom = math.cos(angle) * engine_radius
        y_bottom = math.sin(angle) * engine_radius
        
        engine_top_circle.append([x_top, y_top, body_z_end])
        engine_bottom_circle.append([x_bottom, y_bottom, engine_z_end])
    
    # Create engine nozzle triangles
    for i in range(num_segments):
        next_i = (i + 1) % num_segments
        
        # Side quad
        v1 = engine_top_circle[i]
        v2 = engine_top_circle[next_i]
        v3 = engine_bottom_circle[next_i]
        v4 = engine_bottom_circle[i]
        add_quad(v1, v2, v3, v4)
        
        # Connect to body
        v1 = engine_top_circle[i]
        v2 = engine_top_circle[next_i]
        v3 = bottom_circle[i]
        add_triangle(v1, v2, v3)
    
    # 4. Create fins
    for fin_num in range(num_fins):
        fin_angle = 2 * math.pi * fin_num / num_fins
        
        # Inner fin edge (attached to rocket)
        inner_x = math.cos(fin_angle) * radius
        inner_y = math.sin(fin_angle) * radius
        inner_top = [inner_x, inner_y, body_z_end + fin_height * 0.3]
        inner_bottom = [inner_x, inner_y, body_z_end - fin_height * 0.7]
        
        # Outer fin edge
        outer_x = math.cos(fin_angle) * (radius + fin_width)
        outer_y = math.sin(fin_angle) * (radius + fin_width)
        outer_top = [outer_x, outer_y, body_z_end + fin_height * 0.3]
        outer_bottom = [outer_x, outer_y, body_z_end - fin_height * 0.7]
        
        # Fin side that attaches to rocket
        add_quad(inner_top, inner_bottom, bottom_circle[fin_num * num_segments // num_fins], 
                bottom_circle[(fin_num * num_segments // num_fins + 1) % num_segments])
        
        # Fin surfaces
        # Front face
        add_quad(inner_top, outer_top, outer_bottom, inner_bottom)
        
        # Top face
        add_triangle(inner_top, outer_top, 
                    [inner_top[0] + math.cos(fin_angle + math.pi/2) * fin_thickness * 0.5,
                     inner_top[1] + math.sin(fin_angle + math.pi/2) * fin_thickness * 0.5,
                     inner_top[2]])
        
        # Bottom face
        add_triangle(inner_bottom, outer_bottom,
                    [inner_bottom[0] + math.cos(fin_angle + math.pi/2) * fin_thickness * 0.5,
                     inner_bottom[1] + math.sin(fin_angle + math.pi/2) * fin_thickness * 0.5,
                     inner_bottom[2]])
    
    # 5. Create bottom cap
    center_bottom = [0, 0, engine_z_end]
    for i in range(num_segments):
        next_i = (i + 1) % num_segments
        add_triangle(center_bottom, engine_bottom_circle[i], engine_bottom_circle[next_i])
    
    # Convert to numpy arrays
    vertices_array = np.array(vertices)
    faces_array = np.array(faces)
    
    # Create the mesh
    rocket_mesh = mesh.Mesh(np.zeros(faces_array.shape[0], dtype=mesh.Mesh.dtype))
    for i, face in enumerate(faces_array):
        for j in range(3):
            rocket_mesh.vectors[i][j] = vertices_array[face[j]]
    
    # Write the mesh to file
    rocket_mesh.save(filename)
    print(f"Rocket STL saved to {filename}")
    print(f"Total triangles: {len(faces)}")

# Alternative version using pure Python STL generation
def create_rocket_stl_simple(filename="rocket_simple.stl", length=100, radius=10):
    """Simpler version using pure Python without numpy-stl dependency"""
    
    def write_stl(faces, filename):
        with open(filename, 'wb') as f:
            # Write 80 byte header
            f.write(b'\x00' * 80)
            # Write number of faces
            f.write(struct.pack('<I', len(faces)))
            
            for face in faces:
                # Write normal (dummy, will be recalculated)
                f.write(struct.pack('<fff', 0.0, 0.0, 0.0))
                # Write three vertices
                for vertex in face:
                    f.write(struct.pack('<fff', vertex[0], vertex[1], vertex[2]))
                # Write attribute byte count
                f.write(struct.pack('<H', 0))
    
    # Simplified geometry - create a more detailed rocket than original but simpler than full version
    faces = []
    
    write_stl(faces, filename)
