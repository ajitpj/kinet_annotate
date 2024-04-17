import os, sys, subprocess, nd2
from pathlib import Path
from importlib import reload
import napari
import numpy as np
import pandas as pd
from skimage import measure
from skimage.morphology import white_tophat, disk, ball
from skimage.filters import median, threshold_otsu, gaussian
from skimage.morphology import opening, remove_small_objects, label
from scipy.ndimage import binary_fill_holes
from magicgui import magicgui, widgets
from magicclass import magicclass, MagicTemplate
from magicclass.widgets import PushButton, Select, ComboBox, Slider
from magicclass import field
from napari.types import ImageData, ArrayLike, LayerDataTuple
from typing import List, Dict
from kinet_annotate_defaults import kinet_annotate_defaults



@magicclass
class roi_annotate(MagicTemplate):

    @magicclass(layout="vertical")
    class Frame2:
        file_select   = field(Select, options={'choices': ['1','2']})
        thresh_slider = field(Slider, label="Int. threshold")
        maxproj_butt  = field(PushButton, label="Max. intensity Projection")

    @magicclass(layout="vertical")
    class Frame1:
        proc_but  = field(PushButton)

    @magicclass(layout="horizontal")
    class Frame3:
        save_butt = field(PushButton)

    def __init__(self, file_list: Dict, viewer: napari.Viewer):
         super().__init__()
         self.w_dir = Path(os.getcwd())
         self.data_dict = {}
         self.current_refstack = []
         self.current_tarstack = []
         self.Frame2.file_select.options = file_list
         self.default_pars = kinet_annotate_defaults()
 
    def __post_init__(self, ):
         self.Frame1.proc_but.text  = 'Process'
         self.Frame3.save_butt.text = 'Save all data...'

    # def _roi_to_range(self, roi):
#         roi = roi.astype(np.int16)
#         xstart = np.min(roi[:,0])
#         xend   = np.max(roi[:,0])
#         ystart = np.min(roi[:,1])
#         yend   = np.max(roi[:,1])
#         return xstart, xend, ystart, yend
    
    def _process_disp(self, stack: ImageData, threshold = 0, display=True):
         # Detects kinetochores.
         
         if threshold == 0:
            threshold = threshold_otsu(stack)*self.default_pars.thresh_mult
         
         stack_mask = opening(stack > threshold, 
                              self.default_pars.open_footprint)
         stack_mask = remove_small_objects(stack_mask, 
                                          self.default_pars.min_kinet_size)
         if display:
             layer_name = 'kinetochores'
             if layer_name in self.parent_viewer.layers:
                 self.parent_viewer.layers[layer_name].data = stack_mask.astype(int)
             else:
                self.parent_viewer.add_image(stack_mask, 
                            colormap='green', blending="additive", 
                            visible=True, opacity=0.2,
                            name=layer_name)
        
         return threshold, stack_mask
    
    def _calculate_signal(self, stack: ImageData, kinet_mask: ImageData, cell_mask: ImageData):
        # stack = raw data
        # mask  = kinetochore mask - already trimmed to current cell
        # cell  = current region
        signal = stack * kinet_mask
        signal = np.ravel(signal[signal > 0])
        
        bkg    = stack * ~kinet_mask * cell_mask
        bkg    = np.ravel(bkg[bkg > 0])
        
        return signal.mean(), bkg.mean(), signal, bkg
    

    @Frame2.file_select.connect
    def _select_stack(self):
        self.current_file_id = self.Frame2.file_select.value[0]
        
        tmp = nd2.imread(self.current_file_id)
        self.current_refstack = tmp[:, 1, :, :]
        self.current_tarstack = tmp[:, 0, :, :]

        # Remove previous layers
        num_layers = len(self.parent_viewer.layers)
        if num_layers>0:
            for i in np.arange(num_layers):
                self.parent_viewer.layers.remove(self.parent_viewer.layers[-1])

        # Add new layers and images
        self.parent_viewer.add_image(self.current_refstack, 
                                     name=self.Frame2.file_select.value[0].stem+"_reference",
                                     visible=True)
        self.parent_viewer.add_image(self.current_tarstack, 
                                     name=self.Frame2.file_select.value[0].stem+"_target", 
                                     visible=False,
                                     colormap='magma',
                                     blending="additive")
        self.bkg_subtracted = white_tophat(self.current_refstack, 
                                           self.default_pars.bkg_footprint)
        self.bkg_subtracted = gaussian(self.bkg_subtracted, 
                                       sigma=self.default_pars.gauss_width,
                                       preserve_range=True)
        
        # Set up shape layers for the pre-defined annotations
        cell_cats = self.default_pars.combo_labels
        colors    = self.default_pars.combo_colors
        mask_size = self.current_refstack.shape

        for i, category in enumerate(cell_cats):
            self.parent_viewer.add_layer(napari.layers.Labels(np.zeros((mask_size[1], 
                                                                        mask_size[2]),
                                                                        dtype=int), 
                                         name=category,))
            self.parent_viewer.layers[category].brush_size = 3
            self.parent_viewer.layers[category].color = {1:colors[i+1]}
    
        # Find the threshold for the bkg subtracted image
        threshold, _ = self._process_disp(self.bkg_subtracted,
                                                   0, False)
        # Adjust threshold slider
        threshold = int(threshold)
        self.Frame2.thresh_slider.value = threshold
        self.Frame2.thresh_slider.min = threshold - 30
        self.Frame2.thresh_slider.max = threshold + 30
        
        return
    
    @Frame2.thresh_slider.connect
    def _threshold_display(self):
         new_threshold = self.Frame2.thresh_slider.value
         threshold, stack_mask = self._process_disp(self.bkg_subtracted, 
                                                    threshold=new_threshold,
                                                    display=True)
    
    @Frame2.maxproj_butt.connect
    def _maxproj_display(self):
        self.parent_viewer.add_image(np.max(self.bkg_subtracted, 0),
                                            name="Max. intensity projection",
                                            blending="additive")
                                                
    @Frame1.proc_but.connect
    def _process_stack(self):
        # Go through each shape layer and measure kinetochores
        cell_cats = self.default_pars.combo_labels
        # Set up lists for collecting data, which will be rollde into 
        # a dataframe at the end of the loop.
        cell_id    = []
        annotation = []
        threshold  = []
        centroid   = []
        tar_signal = []
        tar_bkg    = []
        tar_bkg_pix= []
        tar_pixels = []
        ref_signal = []
        ref_bkg    = []
        ref_pixels = []
        ref_bkg_pix= []

        ##
        # Go through each category and measure each user-defined ROI
        for category in cell_cats:
            cell_mask = self.parent_viewer.layers[category].data
            labeled_cells = label(binary_fill_holes(cell_mask))
            
            for i in np.arange(labeled_cells.max()):
                kinet_mask = self.parent_viewer.layers["kinetochores"].data
                # Cell ID & annotation
                cell_id.append('cell_'+str(i))
                annotation.append(category)
                # Centroid of the cell and threshold used
                current_cell = labeled_cells==i+1
                centroid.append(measure.regionprops(label(current_cell))[0].centroid)
                threshold.append(self.Frame2.thresh_slider.value)
                # Calculate the signal, bkg, etc.
                kinet_mask = np.logical_and(kinet_mask, current_cell)
                
                target = self._calculate_signal(self.current_tarstack[self.default_pars.drop_first_+1::, :, :],
                                                kinet_mask[self.default_pars.drop_first_+1::, :, :],
                                                current_cell)
                tar_signal.append(target[0])
                tar_bkg.append(target[1])
                tar_pixels.append(target[2])
                tar_bkg_pix.append(target[3])

                reference = self._calculate_signal(self.current_refstack[self.default_pars.drop_first_+1::, :, :],
                                                   kinet_mask[self.default_pars.drop_first_+1::, :, :],
                                                   current_cell)
                ref_signal.append(reference[0])
                ref_bkg.append(reference[1])
                ref_pixels.append(reference[2])
                ref_bkg_pix.append(reference[3])
                
                
        # to store all the data
        analysis_df = pd.DataFrame({"cell_id"    : cell_id, 
                                    "annotation" : annotation,
                                    "centroid"   : centroid,
                                    "threshold"  : threshold,
                                    "tar_signal" : tar_signal,
                                    "tar_pixels" : tar_pixels,
                                    "tar_bkg_pix": tar_bkg_pix,
                                    "tar_bkg"    : tar_bkg,
                                    "ref_signal" : ref_signal,
                                    "ref_bkg"    : ref_bkg,
                                    "ref_pixels" : ref_pixels,
                                    "ref_bkg_pix": ref_bkg_pix })

        ##  
        self.data_dict[str(self.current_file_id)] = analysis_df
        # self.parent_viewer.add_image(signal)

    @Frame3.save_butt.connect
    def _save_data(self):
        import json
        to_be_saved = pd.DataFrame()
        for key in self.data_dict:
            print(key)
            temp = self.data_dict[key]
            temp["file_id"] = key
            to_be_saved = pd.concat([to_be_saved,temp])
            
        to_be_saved.to_excel(self.current_file_id.parent / 'Analysis.xlsx')