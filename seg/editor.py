from pathlib import Path
import ipywidgets as widgets
from IPython.display import display, HTML
from utils.functions import debounce
from OCC.Display.WebGl.threejs_renderer import ThreejsRenderer

from visualization.jupyter_segmentation_viewer import SegmentationViewer

class MultiSelectJupyterRenderer2(ThreejsRenderer):
    def __init__(self, *args, **kwargs):
        super(MultiSelectJupyterRenderer2, self).__init__(*args, **kwargs)
        
        self._selected_shapes = dict()
        
        self._debug_output = widgets.Output()
        self._debug_enabled = True
        
        self.segment_id_input = widgets.Text(
            placeholder='Enter segmentation ID (0-7)',
            description='Seg ID:',
            disabled=False
        )
        
        display("0:ExtrudeSide , 1: ExtrudeEnd, 2:CutSide, 3:CutEnd, 4: Fillet, 5:Chamfer, 6:RevolveSide, 7:RevolveEnd")
        display(self.segment_id_input)
        display(self._debug_output)
        
        
        
        
    def _debug_log(self, message, level="INFO"):
        """Helper function to log debug messages"""
        if self._debug_enabled:
            with self._debug_output:
                print(f"[{level}] : {message}")
                      
    def clear_selection(self):
        for obj in self._selected_shapes.values():
            obj.material.color = self._default_shape_color
                
        self._selected_shapes.clear()
        
        for callback in self._select_callbacks:
            callback([])
        
    def handle_click(self, value):
        try:
            obj = value.owner.object
            self.clicked_obj = obj
            
            if self._current_mesh_selection != obj:
                if obj is not None:
                    id_clicked = obj.name  # the mesh id clicked
                    self._debug_log(f"object id {id_clicked}")
                    # Toggle selection: add or remove from _selected_shapes
                    if id_clicked in self._selected_shapes:
                        # Deselect: restore original color and remove from selection
                        obj.material.color = self._default_shape_color
                        del self._selected_shapes[id_clicked]
                    else:
                        # Select: store original material and apply selection material
                        self._selected_shapes[id_clicked] = obj
                        obj.material.color = self._selection_color

            
            selected_shapes = [self._shapes[k] for k in self._selected_shapes.keys()]
            for callback in self._select_callbacks:
                callback(selected_shapes)
        
        except Exception as e:
            self.html.value = f"{str(e)}"
           
    def click(self, value):
        """ called whenever a shape  or edge is clicked
        """
        debounce(self.handle_click, 500)(value)
    
    def set_segment_id_change(self, callback):
     
        self.segment_id_input.observe(callback, names='value')

class CADSegmentationEditor(SegmentationViewer):
    def __init__(self, file_stem, step_folder, seg_folder=None, logit_folder=None):
        super(CADSegmentationEditor, self).__init__(file_stem, step_folder, seg_folder, logit_folder)
        
        self._debug_output = widgets.Output()
        self._debug_enabled = True
        
        self._seg = dict()
        self._current_seg_id = 0
        
        self.renderer = MultiSelectJupyterRenderer2()
        self.view_segmentation()
        self.renderer.render()
        
        display(self._debug_output)
    
    def _debug_log(self, message, level="INFO"):
        """Helper function to log debug messages"""
        if self._debug_enabled:
            with self._debug_output:
                print(f"[{level}] : {message}")
    
    def select_face_callback(self, faces):
        if self._current_seg_id is None and len(faces) == 0:
            return
        
         # Ensure the current segment ID exists in the segmentation dictionary
        if self._current_seg_id not in self._seg:
            self._seg[self._current_seg_id] = []
            
        # Safely process the faces and add their indices to the current segment
        face_indices = [self.entity_mapper.face_index(f) for f in faces]
        
        # remove face_indices from other segments
        for seg_id, seg_faces in self._seg.items():
            if seg_id != self._current_seg_id:
                self._seg[seg_id] = [face for face in seg_faces if face not in face_indices]
            
        # Add face_indices to the current segment
        self._seg[self._current_seg_id].extend(face_indices)
        self._debug_log(f"Segment {self._current_seg_id} updated with {len(face_indices)} faces")

    def handle_segment_change(self, change):
        # clear renderer selection list on segment change
        self.renderer.clear_selection()

        try:
            seg_id = int(change['new'])
            assert 0 <= seg_id <= 7, "Segmentation ID must be between 0 and 7"
            self._current_seg_id = seg_id
            self.renderer._selection_color = self.format_color(self.bit8_colors[seg_id])
            self._debug_log(f"Segmentation ID set to {seg_id}")
        except (ValueError, AssertionError) as e:
            self._debug_log(f"Invalid segmentation ID: {str(e)}", level="ERROR")

    def format_color(self, c):
        return (c[0]/255, c[1]/255, c[2]/255)
    
    def _view_segmentation(self, face_segmentation):
        
        faces = list(self.solid.faces())  # Convert map object to a list
    
        colors = []
        for face, segment in zip(faces, face_segmentation):
            color = self.format_color(self.bit8_colors[segment])
            colors.append(color)
            
            if segment not in self._seg:
                self._seg[segment] = []
                
            self._seg[segment].append(self.entity_mapper.face_index(face.topods_shape()))
            
        self._display_faces_with_colors(faces, colors)

    def _display_faces_with_colors(self, faces, colors):
        """
        Display the solid with each face colored
        with the given color
        """
        output = []
        for face, face_color in zip(faces, colors):
            result = self.renderer.DisplayShape(
                face.topods_shape(),
                color=face_color,
                line_width=1,
                mesh_quality=1
            )

            output.append(result)

        # Add the output data to the pickable objects or nothing get rendered
        # for elem in output:
        #     self.renderer._displayed_pickable_objects.add(elem)                                         

        # Now display the scene
        # self.renderer.Display()

    def view_segmentation(self):
            """
            View the initial segmentation of this file
            """
           
            face_segmentation = self.load_segmentation()
            self._view_segmentation(face_segmentation)
            
            # self.renderer.register_select_callback(self.select_face_callback)
            self.renderer.set_segment_id_change(self.handle_segment_change)
        
    def write_seg(self):
        assert self.seg_pathname is not None, "Segment file path is unknown"
        
        dict = {}
        for key, faces in self._seg.items():
            for face in faces:
                dict[face] = key
            
        if len(dict) == 0:
            return
        
        with open(self.seg_pathname, "w") as file:
            for face in [self.entity_mapper.face_index(f.topods_shape()) for f in self.solid.faces()]:
                if face in dict.keys():
                    file.write(f"{dict[face]}\n")
                else:
                    file.write("0\n")
        
        
if __name__ == "__main__":
    step_folder = Path("./example_files/step_examples")
    seg_folder = step_folder
    step_file_stems = [ f.stem for f in step_folder.glob("*.stp")]

    example_index = 24
    file_stem = step_file_stems[example_index]
    editor = CADSegmentationEditor(file_stem, step_folder, seg_folder)
    # editor.view_segmentation()