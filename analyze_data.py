import os, sys, nd2
from pathlib import Path
import napari
import numpy as np
import pandas as pd
from kinet_annotate_GUI import roi_annotate



#
# parent_dir = Path('/Volumes/CDB-joglekar-lab/Juan Orozco/Data/4) Time-Lapse imaging data/20210929_KT Mitotic behavior/KI-KO experiments/')
# data_dir = parent_dir / '20240301' #'Analysis' #/ 
data_dir = Path('/Users/ajitj/Desktop')
files = list(data_dir.glob('*.nd2'))
#
viewer=napari.Viewer()
v = roi_annotate({'choices': files}, viewer)
viewer.window.add_dock_widget(v)
