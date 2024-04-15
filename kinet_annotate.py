from magicgui import magicgui, widgets
from magicclass import magicclass, MagicTemplate
from magicclass.widgets import Figure, PushButton, ComboBox, Select
from magicclass import field
from napari.types import ImageData, ArrayLike, LayerDataTuple
import numpy as np
import pandas as pd
from typing import List, Dict

parent_dir = Path('/Volumes/CDB-joglekar-lab/Juan Orozco/Data/4) Time-Lapse imaging data/20210929_KT Mitotic behavior/KI-KO experiments/')
data_dir = parent_dir / 'Analysis' #/ '20240301'

files = list(data_dir.glob('*.nd2'))
# from skimage.filters import threshold_otsu
# from skimage.morphology import white_tophat, erosion, square

class kinet_annotate_pars:
        def __init__(self):
            self.combo_labels = ['Metaphase',
                           'Metaphase_few_unaligned',
                           'Metaphase_many_unaligned',
                           'All unaligned']
@magicclass
class roi_Annotate(MagicTemplate):

    @magicclass(layout="horizontal")
    class Frame2:
        file_select = field(Select, options={'choices': ['1','2']})

    @magicclass(layout="vertical")
    class Frame1:
        combo_choices = kinet_annotate_pars()
        label_box = field(ComboBox, options={'choices': combo_choices.combo_labels})
        proc_but  = field(PushButton)

    @magicclass(layout="horizontal")
    class Frame3:
        save_butt = field(PushButton)


    def __init__(self, file_list: Dict, viewer: napari.Viewer):
         super().__init__()
         self.data_to_save = {}
         self.current_refstack = []
         self.current_tarstack = []
         self.Frame2.file_select.options = file_list
 
    def __post_init__(self, ):
         self.Frame1.proc_but.text  = 'Process'
         self.Frame3.save_butt.text = 'Save all data...'

    def _roi_to_range(self, roi):
        roi = roi.astype(np.int16)
        xstart = np.min(roi[:,0])
        xend   = np.max(roi[:,0])
        ystart = np.min(roi[:,1])
        yend   = np.max(roi[:,1])
        return xstart, xend, ystart, yend

    @Frame2.file_select.connect
    def _select_stack(self):
        tmp = nd2.imread(self.Frame2.file_select.value[0])
        self.current_refstack = tmp[:, 1, :, :]
        self.current_tarstack = tmp[:, 0, :, :]
        self.parent_viewer.add_image(self.current_refstack, 
                                     name=self.Frame2.file_select.value[0].stem+"_reference",
                                     visible=True)
        self.parent_viewer.add_image(self.current_tarstack, 
                                     name=self.Frame2.file_select.value[0].stem+"_target", 
                                     visible=False,
                                     colormap='magma',
                                     blending="additive")
        bkg_subtracted = white_tophat(ref_channel, ball(3))
        bkg_subtracted = median(bkg_subtracted, ball(1))
        threshold = threshold_otsu(bkg_subtracted)
        viewer.add_image(opening(bkg_subtracted>1.1*threshold, ball(1.5)), 
                         colormap='gray', blending="additive", 
                         visible=True, name=file.stem+'_kinets')
        return
    
    @Frame1.label_box.connect
    def _define_rois(self):
        self.parent_viewer.add_label(name=self.Frame2.file_select.value[0].stem+"ROIs")
        return
    
    @Frame1.proc_but.connect
    def _process_rois(self):
        print(self.parent_viewer.layers['20240301_pAK165_001ROIs'].data[0])
        xstart, xend, ystart, yend = self._roi_to_range(self.parent_viewer.layers['20240301_pAK165_001ROIs'].data[0])
        bkg_subtract = white_tophat(self.current_refstack, ball(3))
        threshold = threshold_otsu(self.current_refstack[:,xstart:xend, ystart:yend])
        a = np.where(self.current_refstack > threshold)
        self.parent_viewer.add_points(a, name="roi")


#
viewer=napari.Viewer()
v = roi_Annotate({'choices': files}, viewer)
viewer.window.add_dock_widget(v)
