# Class defines the default parameters used for analyzing 
# images.
from skimage.morphology import ball

class kinet_annotate_defaults:
        def __init__(self) -> None:
            self.combo_labels  = ['Metaphase',
                                 'Metaphase_few_unaligned',
                                 'Metaphase_many_unaligned',
                                 'All_unaligned']
            
            self.combo_colors  = {1:'green', 
                                  2:'blue', 
                                  3:'yellow', 
                                  4:'red'}
            
            self.thresh_mult   = 1.2
            self.bkg_footprint = ball(5)
            self.med_footprint = ball(2)
            self.open_footprint= ball(1)
            self.min_kinet_size= 8
            self.drop_first_   = 5
            self.gauss_width   = 0.5