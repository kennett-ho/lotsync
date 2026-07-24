"""
Tekion Sold report importer. Kept separate from importers/tekion.py
since these are two independently-pulled exports with different scope
(currently stocked-in vs. sold) -- see ARCHITECTURE.md for why the
Master List alone can never tell us a vehicle sold.
"""

import pandas as pd

from lotsync.utils.file_resolution import find_upload


def load_tekion_sold(path: str = None) -> pd.DataFrame:
    if path is None:
        # "Sold" alone also matches "Unsold" filenames (it's a literal
        # substring), so exclude those explicitly.
        path = find_upload("Sold", exclude="Unsold")
    return pd.read_csv(path)
