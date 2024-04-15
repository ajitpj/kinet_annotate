import os, sys, nd2
from pathlib import Path
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
from kinet_annotate_GUI import roi_annotate




parent_dir = Path('/Volumes/CDB-joglekar-lab/Juan Orozco/Data/4) Time-Lapse imaging data/20210929_KT Mitotic behavior/KI-KO experiments/')
data_dir = parent_dir / '20240301' #'Analysis' #/ 

files = list(data_dir.glob('*.nd2'))
#
viewer=napari.Viewer()
v = roi_Annotate({'choices': files}, viewer)
viewer.window.add_dock_widget(v)
